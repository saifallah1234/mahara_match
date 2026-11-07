// Placement: frontend/src/state/candidateTraining.ts
import { useEffect, useState } from 'react'
import { useAuth } from './auth'
import * as api from '../api/candidate'

/** Training catalogue and own enrollments. Only the Formations page loads them: three requests, whatever the number of programs. */
export function useCandidateTraining() {
  const auth = useAuth()
  const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'CANDIDATE'
  const [programs, setPrograms] = useState<api.Program[]>([])
  const [sessions, setSessions] = useState<api.TrainingSession[]>([])
  const [enrollments, setEnrollments] = useState<api.Enrollment[]>([])
  const [loading, setLoading] = useState(active)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    if (!active) return
    let live = true
    setLoading(true); setError(null)
    Promise.all([
      api.list<api.Program>('/training/programs/'),
      api.list<api.TrainingSession>('/training/sessions/'),
      api.list<api.Enrollment>('/training/enrollments/'),
    ])
      .then(([nextPrograms, nextSessions, nextEnrollments]) => {
        if (!live) return
        setPrograms(nextPrograms); setSessions(nextSessions); setEnrollments(nextEnrollments)
      })
      .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Chargement impossible.') })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [active, auth.user?.id])

  async function refreshEnrollments() {
    setEnrollments(await api.list<api.Enrollment>('/training/enrollments/'))
  }
  async function act(work: () => Promise<unknown>) {
    setError(null)
    try { await work(); await refreshEnrollments() }
    catch (failure) { setError(failure instanceof Error ? failure.message : 'Opération refusée.') }
  }

  return {
    programs, sessions, enrollments, loading, error,
    enroll: (sessionId: string) => act(() => api.save('/training/enrollments/', { session_id: sessionId }, 'POST')),
    cancelEnrollment: (id: string) => act(() => api.remove(`/training/enrollments/${id}/`)),
  }
}

/** For each offer, one active programme teaching a skill of that offer the candidate lacks (same rule as the baseline match). */
export function useSuggestedTraining(offerIds: string[], ownSkillIds: string[]): Record<string, api.Program> {
  const [suggestions, setSuggestions] = useState<Record<string, api.Program>>({})
  const key = `${offerIds.join()}|${ownSkillIds.join()}`
  useEffect(() => {
    let live = true
    const own = new Set(ownSkillIds)
    void Promise.all(offerIds.map(async (offerId) => {
      const skills = await api.list<{ skill_id: string }>(`/offer-skills/?offer_id=${offerId}`)
      for (const skill of skills.filter((item) => !own.has(item.skill_id))) {
        const [program] = await api.list<api.Program>(`/training/programs/?skill_id=${skill.skill_id}&status=ACTIVE`)
        if (program) return [offerId, program] as const
      }
      return null
    })).then((pairs) => { if (live) setSuggestions(Object.fromEntries(pairs.filter((pair) => pair !== null))) })
      // Suggestions are optional: the dashboard still shows the matches without them.
      .catch(() => {})
    return () => { live = false }
  }, [key])
  return suggestions
}
