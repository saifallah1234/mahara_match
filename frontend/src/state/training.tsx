import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import * as api from '../api/training'
import { listSkills, type SkillRef } from '../api/recruiter'

type State = {
    programs: api.Program[]; sessions: api.Session[]; enrollments: api.Enrollment[]
    skills: api.ProgramSkill[]; skillCatalogue: SkillRef[]
    loading: boolean; error: string | null
    createProgram: (d: api.ProgramInput, skills: { skillId: string; level: api.ProgramSkill['target_level'] }[]) => Promise<string>
    addSkill: (programId: string, skillId: string, level: api.ProgramSkill['target_level']) => Promise<void>
    removeSkill: (id: string) => Promise<void>
    updateProgram: (id: string, d: Partial<api.ProgramInput>) => Promise<void>
    setProgramStatus: (id: string, status: api.Program['status']) => Promise<void>
    createSession: (d: api.SessionInput) => Promise<void>
    updateSession: (id: string, d: api.SessionPatch) => Promise<void>
    setSessionStatus: (id: string, status: api.Session['status']) => Promise<void>
    setProgress: (enrollmentId: string, completionRate: number) => Promise<void>
}
const Context = createContext<State | null>(null)

function explain(err: unknown): string {
  return err instanceof Error ? err.message : 'Opération refusée.'
}

export function TrainingProvider({ children }: { children: ReactNode }) {
    const auth = useAuth()
    const orgId = auth.workspace?.organization?.id
    const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'TRAINING_MANAGER'
    const [programs, setPrograms] = useState<api.Program[]>([])
    const [sessions, setSessions] = useState<api.Session[]>([])
    const [enrollments, setEnrollments] = useState<api.Enrollment[]>([])
    const [skills, setSkills] = useState<api.ProgramSkill[]>([])
    const [skillCatalogue, setSkillCatalogue] = useState<SkillRef[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    const reload = useCallback(async () => {
        if (!active) return
        setLoading(true); setError(null)
        try {
            if (!orgId) return
            const p = await api.listPrograms(orgId)
            const [s, e, k, catalogue] = await Promise.all([
                Promise.all(p.map((pr) => api.listSessions(pr.id))).then((groups) => groups.flat()),
                api.listEnrollments(orgId),
                Promise.all(p.map((pr) => api.listProgramSkills(pr.id))).then((groups) => groups.flat()),
                listSkills(),
            ])
            setPrograms(p); setSessions(s); setEnrollments(e); setSkills(k); setSkillCatalogue(catalogue)
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
        programs, sessions, enrollments, skills, skillCatalogue, loading, error,
        // A program cannot start ACTIVE, so it is created as a draft, given its skills, then activated by the caller.
        createProgram: async (d, chosen) => {
            setError(null)
            try {
                const program = await api.createProgram(d)
                for (const skill of chosen) await api.addProgramSkill(program.id, skill.skillId, skill.level)
                await reload()
                return program.id
            } catch (err) { setError(explain(err)); throw err }
        },
        addSkill: (programId, skillId, level) => run(() => api.addProgramSkill(programId, skillId, level)),
        removeSkill: (id) => run(() => api.removeProgramSkill(id)),
        updateProgram: (id, d) => run(() => api.updateProgram(id, d)),
        setProgramStatus: (id, status) => run(() => api.updateProgram(id, { status })),
        createSession: (d) => run(() => api.createSession(d)),
        updateSession: (id, d) => run(() => api.updateSession(id, d)),
        setSessionStatus: (id, status) => run(() => api.updateSession(id, { status })),
        setProgress: (enrollmentId, completionRate) => run(() => api.updateProgress(enrollmentId, completionRate)),
    }
    return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useTraining() {
    const v = useContext(Context)
    if (!v) throw new Error('TrainingProvider is required.')
    return v
}
