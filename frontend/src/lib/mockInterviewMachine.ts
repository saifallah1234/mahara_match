export type InterviewDisplayState = 'PREPARING' | 'READY' | 'INTRO' | 'SPEAKING' | 'LISTENING' | 'UPLOADING' | 'THINKING' | 'COMPLETED' | 'FAILED' | 'CANCELLED'
export function interviewDisplayState(status: string): InterviewDisplayState {
  if (status === 'IN_PROGRESS') return 'SPEAKING'
  if (status === 'THINKING' || status === 'EVALUATING') return 'THINKING'
  if (['PREPARING', 'READY', 'COMPLETED', 'FAILED', 'CANCELLED'].includes(status)) return status as InterviewDisplayState
  throw new Error('État d’entretien inconnu')
}
export function recordingAllowed(state: InterviewDisplayState) { return state === 'LISTENING' }
export function recordingMimeType(supported: (mime: string) => boolean) {
  return ['audio/webm;codecs=opus', 'audio/webm', 'audio/mp4', 'audio/ogg;codecs=opus'].find(supported) ?? null
}
