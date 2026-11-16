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
// Camera plus microphone kept in browser memory for local replay only; never uploaded.
export function reviewMimeType(supported: (mime: string) => boolean) {
  return ['video/webm;codecs=vp8,opus', 'video/webm', 'video/mp4'].find(supported) ?? null
}
export async function openCapture(getUserMedia: (constraints: MediaStreamConstraints) => Promise<MediaStream>) {
  try {
    const stream = await getUserMedia({ audio: true, video: { facingMode: 'user' } })
    return { stream, audioOnly: !stream.getVideoTracks().length }
  } catch { /* camera missing or refused: retry with the microphone alone */ }
  try { return { stream: await getUserMedia({ audio: true }), audioOnly: true } }
  catch { throw new Error('Le microphone est nécessaire pour répondre. Autorisez son accès dans votre navigateur, puis réessayez.') }
}
export function formatCountdown(seconds: number) {
  return `${Math.floor(seconds / 60)}:${String(seconds % 60).padStart(2, '0')}`
}
