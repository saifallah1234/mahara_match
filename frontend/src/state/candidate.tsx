import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import { request } from '../api/client'
import * as api from '../api/candidate'
import * as matching from '../api/matching'

type Data = {
  profile: api.Profile | null; records: Record<api.RecordKind, api.OwnedRecord[]>;
  cvs: api.CV[]; documents: api.Document[]; offers: api.Offer[];
  applications: api.Application[]; interviews: api.Interview[]; history: api.History[];
  matches: matching.OfferMatch[];
}
/** Groups of workspace data; a save reloads only the groups it changes. */
type Part = 'profile' | 'records' | 'cvs' | 'documents' | 'offers' | 'applications' | 'matches'
const ALL_PARTS: Part[] = ['profile', 'records', 'cvs', 'documents', 'offers', 'applications', 'matches']

const empty = (): Data => ({
  profile: null, records: { experiences: [], educations: [], skills: [], languages: [], certifications: [], projects: [], preferences: [] },
  cvs: [], documents: [], offers: [], applications: [], interviews: [], history: [], matches: [],
})

type CandidateState = Data & {
  loading: boolean; error: string | null; message: string | null; calculating: boolean;
  /** True when a published offer is newer than the latest score calculation. */
  scoresStale: boolean;
  clearMessage: () => void;
  reload: () => Promise<void>;
  saveIdentity: (user: { first_name: string; last_name: string; phone: string }, profile: Partial<api.Profile>) => Promise<void>;
  saveRecord: (kind: api.RecordKind, values: object, id?: string) => Promise<void>;
  deleteRecord: (kind: api.RecordKind, id: string) => Promise<void>;
  uploadCV: (file: File, title: string, documentId?: string) => Promise<string | undefined>;
  setPrimary: (cv: api.CV) => Promise<void>; deleteCV: (cv: api.CV) => Promise<void>;
  apply: (offerId: string, cvId: string, coverLetter: string) => Promise<void>;
  withdraw: (applicationId: string) => Promise<void>;
  calculateMatches: () => Promise<void>;
}
const Context = createContext<CandidateState | null>(null)

const newest = (dates: (string | null)[]) => dates.filter((d): d is string => !!d).sort().reverse()[0] ?? null

async function loadRecords(): Promise<Data['records']> {
  const lists = await Promise.all(Object.values(api.records).map((path) => api.list<api.OwnedRecord>(path)))
  const [experiences, educations, skills, languages, certifications, projects, preferences] = lists
  return { experiences, educations, skills, languages, certifications, projects, preferences }
}

async function fetchPart(part: Part, profileId: string | undefined): Promise<Partial<Data>> {
  switch (part) {
    case 'profile': return { profile: await request<api.Profile>('/candidate-profiles/me/') }
    case 'records': return { records: await loadRecords() }
    case 'cvs': return { cvs: await api.list<api.CV>('/cvs/') }
    case 'documents': return { documents: await api.list<api.Document>('/documents/') }
    case 'offers': return { offers: await api.publishedOffers() }
    case 'matches': return { matches: await api.list<matching.OfferMatch>('/offer-matches/') }
    case 'applications': {
      const [applications, interviews, history] = await Promise.all([
        api.list<api.Application>('/applications/'), api.list<api.Interview>('/interviews/'),
        api.list<api.History>('/application-status-history/'),
      ])
      const own = applications.filter((item) => item.candidate_id === profileId)
      const ownIds = new Set(own.map((item) => item.id))
      return {
        applications: own,
        interviews: interviews.filter((item) => ownIds.has(item.application_id)),
        history: history.filter((item) => ownIds.has(item.application_id)),
      }
    }
  }
}

export function CandidateProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const [data, setData] = useState<Data>(empty)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [calculating, setCalculating] = useState(false)
  const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'CANDIDATE'

  async function refresh(parts: Part[], profileId = data.profile?.id) {
    const groups = await Promise.all(parts.map((part) => fetchPart(part, profileId)))
    setData((current) => Object.assign({}, current, ...groups))
  }

  async function loadAll() {
    const profile = await request<api.Profile>('/candidate-profiles/me/')
    const rest = ALL_PARTS.filter((part) => part !== 'profile')
    const groups = await Promise.all(rest.map((part) => fetchPart(part, profile.id)))
    return Object.assign(empty(), { profile }, ...groups) as Data
  }

  async function reload() {
    if (!active) return
    setLoading(true); setError(null)
    try { setData(await loadAll()) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Chargement impossible.') }
    finally { setLoading(false) }
  }

  useEffect(() => {
    let live = true
    setData(empty()); setMessage(null); setError(null); setLoading(active)
    if (active) void loadAll().then((next) => { if (live) setData(next) })
      .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Chargement impossible.') })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [auth.user?.id, auth.workspace?.role_code, auth.workspace?.organization?.id, active])

  async function confirmed(work: () => Promise<unknown>, success: string, parts: Part[]) {
    setError(null); setMessage(null)
    try { await work(); await refresh(parts); setMessage(success) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Opération refusée.'); throw failure }
  }

  async function calculateMatches() {
    setCalculating(true)
    try {
      const matches = await matching.calculateOfferMatches()
      setData((current) => ({ ...current, matches }))
    } finally { setCalculating(false) }
  }

  const latestOffer = newest(data.offers.map((offer) => offer.published_at))
  const latestScore = newest(data.matches.map((match) => match.calculated_at))
  const value: CandidateState = {
    ...data, loading, error, message, calculating, clearMessage: () => setMessage(null), reload,
    scoresStale: !!latestOffer && (!latestScore || latestOffer > latestScore),
    saveIdentity: (user, profile) => confirmed(async () => {
      await api.save('/users/me/', user)
      await api.save('/candidate-profiles/me/', profile)
      await auth.refreshUser()
    }, 'Profil enregistré.', ['profile']),
    saveRecord: (kind, values, id) => confirmed(async () => {
      await api.save(`${api.records[kind]}${id ? `${id}/` : ''}`, values, id ? 'PATCH' : 'POST')
      // Skill changes move the scores, so they are recalculated straight away.
      if (kind === 'skills') await calculateMatches()
    }, 'Enregistré.', ['records']),
    deleteRecord: (kind, id) => confirmed(async () => {
      await api.remove(`${api.records[kind]}${id}/`)
      // A removed skill moves the scores too.
      if (kind === 'skills') await calculateMatches()
    }, 'Supprimé.', ['records']),
    uploadCV: async (file, title, documentId) => {
      setError(null); setMessage(null)
      try { const result = await api.uploadCV(file, title, documentId); await refresh(['cvs', 'documents']); setMessage('CV importé.'); return result.documentId }
      catch (failure) { setError(failure instanceof Error ? failure.message : 'Import impossible.'); throw failure }
    },
    setPrimary: (cv) => confirmed(() => api.save(`/cvs/${cv.id}/`, { is_primary: true }), 'CV principal mis à jour.', ['cvs']),
    deleteCV: (cv) => confirmed(() => api.remove(`/cvs/${cv.id}/`), 'CV supprimé de votre liste.', ['cvs']),
    apply: (offerId, cvId, coverLetter) => confirmed(() => api.save('/applications/', { offer_id: offerId, cv_id: cvId, cover_letter: coverLetter }, 'POST'), 'Candidature déposée.', ['applications']),
    withdraw: (id) => confirmed(() => api.save(`/applications/${id}/transition/`, { status: 'WITHDRAWN' }, 'POST'), 'Candidature retirée.', ['applications']),
    calculateMatches: () => confirmed(calculateMatches, 'Compatibilité calculée.', []),
  }
  return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useCandidate() {
  const value = useContext(Context)
  if (!value) throw new Error('CandidateProvider is required.')
  return value
}
