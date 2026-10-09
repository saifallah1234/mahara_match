import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import { request } from '../api/client'
import * as api from '../api/candidate'

type Data = {
  profile: api.Profile | null; records: Record<api.RecordKind, api.OwnedRecord[]>;
  cvs: api.CV[]; documents: api.Document[]; offers: api.Offer[];
  applications: api.Application[]; interviews: api.Interview[]; history: api.History[];
  programs: api.Program[]; sessions: api.TrainingSession[]; enrollments: api.Enrollment[];
}
const empty = (): Data => ({
  profile: null, records: { experiences: [], educations: [], skills: [], languages: [], certifications: [], projects: [], preferences: [] },
  cvs: [], documents: [], offers: [], applications: [], interviews: [], history: [], programs: [], sessions: [], enrollments: [],
})
type CandidateState = Data & {
  loading: boolean; error: string | null; message: string | null;
  clearMessage: () => void;
  reload: () => Promise<void>;
  saveIdentity: (user: { first_name: string; last_name: string; phone: string }, profile: Partial<api.Profile>) => Promise<void>;
  saveRecord: (kind: api.RecordKind, values: object, id?: string) => Promise<void>;
  uploadCV: (file: File, title: string, documentId?: string) => Promise<string | undefined>;
  setPrimary: (cv: api.CV) => Promise<void>; deleteCV: (cv: api.CV) => Promise<void>;
  apply: (offerId: string, cvId: string, coverLetter: string) => Promise<void>;
  withdraw: (applicationId: string) => Promise<void>;
  enroll: (sessionId: string) => Promise<void>; cancelEnrollment: (id: string) => Promise<void>;
}
const Context = createContext<CandidateState | null>(null)

export function CandidateProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const [data, setData] = useState<Data>(empty)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'CANDIDATE'

  async function load(): Promise<Data> {
    const [profile, recordLists, cvs, documents, offers, applications, interviews, history, programs, enrollments] = await Promise.all([
      request<api.Profile>('/candidate-profiles/me/'),
      Promise.all(Object.values(api.records).map((path) => api.list<api.OwnedRecord>(path))),
      api.list<api.CV>('/cvs/'), api.list<api.Document>('/documents/'), api.publishedOffers(),
      api.list<api.Application>('/applications/'), api.list<api.Interview>('/interviews/'),
      api.list<api.History>('/application-status-history/'), api.list<api.Program>('/training/programs/'),
      api.list<api.Enrollment>('/training/enrollments/'),
    ])
    const [experiences, educations, skills, languages, certifications, projects, preferences] = recordLists
    const sessions = (await Promise.all(programs.map((p) => api.list<api.TrainingSession>(`/training/sessions/?program_id=${p.id}`)))).flat()
    const ownApplications = applications.filter((item) => item.candidate_id === profile.id)
    const ownIds = new Set(ownApplications.map((item) => item.id))
    return { profile, records: { experiences, educations, skills, languages, certifications, projects, preferences }, cvs, documents, offers, applications: ownApplications, interviews: interviews.filter((item) => ownIds.has(item.application_id)), history: history.filter((item) => ownIds.has(item.application_id)), programs, sessions, enrollments: enrollments.filter((item) => item.candidate_id === profile.id) }
  }
  async function reload() {
    if (!active) return
    setLoading(true); setError(null)
    try { setData(await load()) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Chargement impossible.') }
    finally { setLoading(false) }
  }
  useEffect(() => {
    let live = true
    setData(empty()); setMessage(null); setError(null); setLoading(active)
    if (active) void load().then((next) => { if (live) setData(next) })
      .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Chargement impossible.') })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [auth.user?.id, auth.workspace?.role_code, auth.workspace?.organization?.id, active])

  async function confirmed(work: () => Promise<unknown>, success: string) {
    setError(null); setMessage(null)
    try { await work(); await reload(); setMessage(success) }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Opération refusée.'); throw failure }
  }
  const value: CandidateState = {
    ...data, loading, error, message, clearMessage: () => setMessage(null), reload,
    saveIdentity: (user, profile) => confirmed(async () => {
      await api.save('/users/me/', user)
      await api.save('/candidate-profiles/me/', profile)
      await auth.refreshUser()
    }, 'Profil enregistré.'),
    saveRecord: (kind, values, id) => confirmed(() => api.save(`${api.records[kind]}${id ? `${id}/` : ''}`, values, id ? 'PATCH' : 'POST'), 'Enregistré.'),
    uploadCV: async (file, title, documentId) => {
      setError(null); setMessage(null)
      try { const result = await api.uploadCV(file, title, documentId); await reload(); setMessage('CV importé.'); return result.documentId }
      catch (failure) { setError(failure instanceof Error ? failure.message : 'Import impossible.'); throw failure }
    },
    setPrimary: (cv) => confirmed(() => api.save(`/cvs/${cv.id}/`, { is_primary: true }), 'CV principal mis à jour.'),
    deleteCV: (cv) => confirmed(() => api.remove(`/cvs/${cv.id}/`), 'CV supprimé de votre liste.'),
    apply: (offerId, cvId, coverLetter) => confirmed(() => api.save('/applications/', { offer_id: offerId, cv_id: cvId, cover_letter: coverLetter }, 'POST'), 'Candidature déposée.'),
    withdraw: (id) => confirmed(() => api.save(`/applications/${id}/transition/`, { status: 'WITHDRAWN' }, 'POST'), 'Candidature retirée.'),
    enroll: (sessionId) => confirmed(() => api.save('/training/enrollments/', { session_id: sessionId }, 'POST'), 'Inscription enregistrée.'),
    cancelEnrollment: (id) => confirmed(() => api.remove(`/training/enrollments/${id}/`), 'Inscription annulée.'),
  }
  return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useCandidate() {
  const value = useContext(Context)
  if (!value) throw new Error('CandidateProvider is required.')
  return value
}
