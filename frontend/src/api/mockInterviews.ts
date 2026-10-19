import { request } from './client.ts'

export interface InterviewTurn {
  id: string; kind: 'MAIN' | 'FOLLOWUP'; position: number | null; question: string; answer: string
}
export interface Playback { video?: string | null; audio?: string | null; avatar?: string; simulated?: boolean; lip_synced?: boolean }
export interface InterviewSession {
  id: string; status: string; version: number; current_turn_id: string | null; turns: InterviewTurn[]
  jobs: { id: string; stage: string; status: string; error_code: string; simulated: boolean }[]
  allowed_actions: string[]; availability: { simulated: boolean }; error_code: string
  playback: { introduction: string | null; closing_audio: string | null; neutral_avatar: string; thinking_avatar: string; listening_avatar: string; turn: Playback | null }
}
export interface InterviewFeedback { summary: string; questions: { turn_id: string; strengths: string[]; gaps: string[]; excerpts: string[]; improvements: string[] }[] }
const root = '/mock-interviews/'
export const interviewHistory = (page = 1) => request<{ results: InterviewSession[]; next: string | null }>(`${root}?page=${page}`)
export const getInterview = (id: string) => request<InterviewSession>(`${root}${id}/`)
export const createInterview = (offerId: string, cvId: string | undefined, key: string) => request<InterviewSession>(root, { method: 'POST', headers: { 'Idempotency-Key': key }, body: JSON.stringify({ offer_id: offerId, cv_id: cvId || undefined, language: 'fr' }) })
export const interviewAction = (id: string, action: 'start' | 'retry' | 'cancel') => request<InterviewSession>(`${root}${id}/${action}/`, { method: 'POST' })
export const getInterviewFeedback = (id: string) => request<InterviewFeedback>(`${root}${id}/feedback/`)
export function answerInterview(session: InterviewSession, turnId: string, blob: Blob, key: string) {
  const body = new FormData()
  body.set('recording', blob, blob.type.includes('webm') ? 'answer.webm' : 'answer.wav')
  body.set('version', String(session.version))
  return request<InterviewSession>(`${root}${session.id}/turns/${turnId}/answer/`, { method: 'POST', headers: { 'Idempotency-Key': key }, body })
}
