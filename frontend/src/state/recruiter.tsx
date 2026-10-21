import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import * as api from '../api/recruiter'

type SkillChoice = { id: string; mandatory: boolean }

type State = {
  offers: api.RecruiterOffer[]
  applications: api.RecruiterApplication[]
  interviews: api.RecruiterInterview[]
  skills: api.SkillRef[]
  loading: boolean
  error: string | null
  reload: () => Promise<void>
  createOffer: (data: api.OfferInput) => Promise<string>
  updateOffer: (id: string, data: Partial<api.OfferInput>) => Promise<void>
  syncOfferSkills: (offerId: string, chosen: SkillChoice[], current: api.OfferSkill[]) => Promise<void>
  setOfferStatus: (id: string, status: api.RecruiterOffer['status']) => Promise<void>
  publishOffer: (id: string) => Promise<void>
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

  const run = async <T,>(work: () => Promise<T>): Promise<T> => {
    setError(null)
    try {
      const result = await work()
      await reload()
      return result
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Opération refusée.')
      throw e
    }
  }

  const mutate = async (work: () => Promise<unknown>) => { await run(work) }
  const skillName = (id: string) => skills.find((s) => s.id === id)?.canonical_name ?? 'inconnue'
  // Names the skill in the message, so the recruiter knows which one did not save.
  const saving = async (skillId: string, work: () => Promise<unknown>) => {
    try {
      await work()
    } catch (e) {
      throw new Error(`Compétence « ${skillName(skillId)} » non enregistrée : ${e instanceof Error ? e.message : 'erreur'}`)
    }
  }

  const value: State = {
    offers, applications, interviews, skills, loading, error, reload,
    createOffer: (data) => run(async () => (await api.createOffer(data)).id),
    updateOffer: (id, data) => mutate(() => api.updateOffer(id, data)),
    syncOfferSkills: (offerId, chosen, current) => mutate(async () => {
      for (const row of current) {
        if (!chosen.some((c) => c.id === row.skill_id)) await saving(row.skill_id, () => api.deleteOfferSkill(row.id))
      }
      for (const c of chosen) {
        const row = current.find((x) => x.skill_id === c.id)
        if (!row) await saving(c.id, () => api.addOfferSkill(offerId, c.id, c.mandatory))
        else if (row.is_mandatory !== c.mandatory) await saving(c.id, () => api.updateOfferSkill(row.id, c.mandatory))
      }
    }),
    setOfferStatus: (id, status) => mutate(() => api.transitionOffer(id, status)),
    publishOffer: (id) => mutate(async () => {
      try {
        await api.transitionOffer(id, 'PUBLISHED')
      } catch (e) {
        throw new Error(`Publication impossible : ${e instanceof Error ? e.message : 'erreur'}`)
      }
    }),
    moveApplication: (id, status, reason) => mutate(() => api.transitionApplication(id, status, reason)),
    scheduleInterview: (data) => mutate(() => api.scheduleInterview(data)),
    setInterviewStatus: (id, status, feedback) => mutate(() => api.transitionInterview(id, status, feedback)),
  }
  return <Context.Provider value={value}>{children}</Context.Provider>
}

export function useRecruiter() {
  const v = useContext(Context)
  if (!v) throw new Error('RecruiterProvider is required.')
  return v
}
