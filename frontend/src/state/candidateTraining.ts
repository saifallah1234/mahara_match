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
