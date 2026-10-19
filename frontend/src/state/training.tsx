import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import * as api from '../api/training'

type State = {
    programs: api.Program[]; sessions: api.Session[]; enrollments: api.Enrollment[]
    loading: boolean; error: string | null
    createProgram: (d: api.ProgramInput) => Promise<void>
    setProgramStatus: (id: string, status: api.Program['status']) => Promise<void>
    createSession: (d: api.SessionInput) => Promise<void>
    setSessionStatus: (id: string, status: api.Session['status']) => Promise<void>
}
const Context = createContext<State | null>(null)

function explain(err: unknown): string {
  const details = (err as { details?: unknown }).details
  if (details && typeof details === 'object') {
    const parts = Object.entries(details as Record<string, unknown>).map(
      ([field, value]) => `${field} : ${Array.isArray(value) ? value.join(' ') : String(value)}`,
    )
    if (parts.length) return parts.join(' — ')
  }
  return err instanceof Error ? err.message : 'Opération refusée.'
}

export function TrainingProvider({ children }: { children: ReactNode }) {
    const auth = useAuth()
    const orgId = auth.workspace?.organization?.id
    const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'TRAINING_MANAGER'
    const [programs, setPrograms] = useState<api.Program[]>([])
    const [sessions, setSessions] = useState<api.Session[]>([])
    const [enrollments, setEnrollments] = useState<api.Enrollment[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const reload = useCallback(async () => {
        if (!active) return
        setLoading(true); setError(null)
        try {
            if (!orgId) return
            const p = await api.listPrograms(orgId)
            const [s, e] = await Promise.all([
                Promise.all(p.map((pr) => api.listSessions(pr.id))).then((groups) => groups.flat()),
                api.listEnrollments(orgId),
            ])
            setPrograms(p); setSessions(s); setEnrollments(e)
        } catch (err) {
            setError(err instanceof Error ? err.message : 'Chargement impossible.')
        } finally { setLoading(false) }
    }, [active, orgId])
    useEffect(() => { void reload() }, [reload])

    const run = async (work: () => Promise<unknown>) => {
        setError(null)
        try { await work(); await reload() }
            catch (err) { setError(explain(err)); throw err }
    }
    const value: State = {
        programs, sessions, enrollments, loading, error,
        createProgram: (d) => run(() => api.createProgram(d)),
        setProgramStatus: (id, status) => run(() => api.updateProgram(id, { status })),
        createSession: (d) => run(() => api.createSession(d)),
        setSessionStatus: (id, status) => run(() => api.updateSession(id, { status })),
    }
    return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useTraining() {
    const v = useContext(Context)
    if (!v) throw new Error('TrainingProvider is required.')
    return v
}
