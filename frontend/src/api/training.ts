import { allPages } from './auth.ts'
import { request } from './client.ts'

export type Program = {
  id: string; organization_id: string; organization_name: string; title: string; description: string
  level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED'; delivery_mode: 'ONLINE' | 'PRESENTIAL' | 'HYBRID'
  status: 'DRAFT' | 'ACTIVE' | 'ARCHIVED'; is_free: boolean; price: string
}
export type Session = {
  id: string; program: string; start_date: string; end_date: string; capacity: number
  location_or_url: string; registration_deadline: string; status: 'PLANNED' | 'ONGOING' | 'COMPLETED' | 'CANCELLED'
}
export type Enrollment = {
  id: string; session: string; candidate_id: string; applicant: { first_name: string; last_name: string; email: string }
  program_title: string; session_start_date: string
  status: 'REGISTERED' | 'IN_PROGRESS' | 'COMPLETED' | 'DROPPED'; enrolled_at: string; completion_rate: string | null
}
export type ProgramInput = Pick<Program, 'title' | 'description' | 'level' | 'delivery_mode' | 'status' | 'is_free'> & {
  organization_id: string; price: number
}
export type SessionInput = {
  program_id: string; start_date: string; end_date: string; capacity: number
  location_or_url: string; registration_deadline: string
}

const send = <T>(method: string, path: string, body?: object) =>
  request<T>(path, { method, body: body ? JSON.stringify(body) : undefined })

export const listPrograms = (organizationId: string) =>
  allPages<Program>(`/training/programs/?organization_id=${organizationId}`)
export const listSessions = (programId: string) =>
  allPages<Session>(`/training/sessions/?program_id=${programId}`)
export const listEnrollments = (organizationId?: string) =>
  allPages<Enrollment>(`/training/enrollments/${organizationId ? `?organization_id=${organizationId}` : ''}`)
export const createProgram = (d: ProgramInput) => send<Program>('POST', '/training/programs/', d)
export const updateProgram = (id: string, d: Partial<ProgramInput>) => send<Program>('PATCH', `/training/programs/${id}/`, d)
export const createSession = (d: SessionInput) => send<Session>('POST', '/training/sessions/', d)
export const updateSession = (id: string, d: Partial<{ status: Session['status'] }>) => send<Session>('PATCH', `/training/sessions/${id}/`, d)
export type ProgramSkill = {
  id: string; program: string; skill_id: string
  target_level: 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT'; purpose: string
}
export const listProgramSkills = (programId: string) =>
  allPages<ProgramSkill>(`/training/skills/?program_id=${programId}`)
export const addProgramSkill = (programId: string, skillId: string, targetLevel: ProgramSkill['target_level']) =>
  send<ProgramSkill>('POST', '/training/skills/', { program_id: programId, skill_id: skillId, target_level: targetLevel })
export const removeProgramSkill = (id: string) => send<void>('DELETE', `/training/skills/${id}/`)
