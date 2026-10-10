import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import * as api from '../api/recruiter'

type State = {
  offers: api.RecruiterOffer[]
  applications: api.RecruiterApplication[]
  interviews: api.RecruiterInterview[]
  skills: api.SkillRef[]
  loading: boolean
  error: string | null
  reload: () => Promise<void>
  createOffer: (data: api.OfferInput, skills: { id: string; mandatory: boolean }[], publish: boolean) => Promise<void>
  setOfferStatus: (id: string, status: api.RecruiterOffer['status']) => Promise<void>
  moveApplication: (id: string, status: string, reason?: string) => Promise<void>
  scheduleInterview: (data: api.InterviewInput) => Promise<void>
  setInterviewStatus: (id: string, status: 'COMPLETED' | 'CANCELLED', feedback?: string) => Promise<void>
}
const Context = createContext<State | null>(null)

export function RecruiterProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const orgId = auth.workspace?.organization?.id
  const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'RECRUITER'
  const [offers, setOffers] = useState<api.RecruiterOffer[]>([])
  const [applications, setApplications] = useState<api.RecruiterApplication[]>([])
  const [interviews, setInterviews] = useState<api.RecruiterInterview[]>([])
  const [skills, setSkills] = useState<api.SkillRef[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!active) return
    setLoading(true); setError(null)
    try {
      const [o, a, s, i] = await Promise.all([
        api.listOffers(orgId), api.listApplications(), api.listSkills(), api.listInterviews(),
      ])
      const mine = a.filter((x) => o.some((offer) => offer.id === x.offer_id))
      setOffers(o); setApplications(mine); setSkills(s)
      setInterviews(i.filter((x) => mine.some((app) => app.id === x.application_id)))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Chargement impossible.')
    } finally {
      setLoading(false)
    }
  }, [active, orgId])
  useEffect(() => { void reload() }, [reload])

  const run = async (work: () => Promise<unknown>) => {
    setError(null)
    try { await work(); await reload() }
    catch (e) { setError(e instanceof Error ? e.message : 'Opération refusée.'); throw e }
  }

  const value: State = {
    offers, applications, interviews, skills, loading, error, reload,
    createOffer: (data, chosen, publish) => run(async () => {
      const offer = await api.createOffer(data)
      for (const s of chosen) await api.addOfferSkill(offer.id, s.id, s.mandatory)
      if (publish) await api.transitionOffer(offer.id, 'PUBLISHED')
    }),
    setOfferStatus: (id, status) => run(() => api.transitionOffer(id, status)),
    moveApplication: (id, status, reason) => run(() => api.transitionApplication(id, status, reason)),
    scheduleInterview: (data) => run(() => api.scheduleInterview(data)),
    setInterviewStatus: (id, status, feedback) => run(() => api.transitionInterview(id, status, feedback)),
  }
  return <Context.Provider value={value}>{children}</Context.Provider>
}

export function useRecruiter() {
  const v = useContext(Context)
  if (!v) throw new Error('RecruiterProvider is required.')
  return v
}