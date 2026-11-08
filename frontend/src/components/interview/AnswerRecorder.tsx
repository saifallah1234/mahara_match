import { useEffect, useRef, useState, type ReactNode } from 'react'
import { formatCountdown, openCapture, recordingMimeType, reviewMimeType } from '../../lib/mockInterviewMachine'
import { Button } from '../ui'
import { CameraIdle, InterviewStage, STAGE_FRAME } from './InterviewStage'

const LIMIT_SECONDS = 180
type Phase = 'opening' | 'preview' | 'recording' | 'review' | 'blocked'
const STATUS: Record<Phase | 'lastMinute', string> = {
  opening: 'Activation de la caméra…',
  preview: 'Caméra active : démarrez l’enregistrement quand vous êtes prêt.',
  recording: 'Enregistrement en cours',
  lastMinute: 'Enregistrement en cours : moins d’une minute restante',
  review: 'Enregistrement terminé : revoyez votre réponse avant de l’envoyer.',
  blocked: 'Enregistrement impossible',
}

export function AnswerRecorder({ onSubmit, busy, interviewer, cancel }: { onSubmit: (blob: Blob, key: string) => Promise<void>; busy: boolean; interviewer: ReactNode; cancel?: ReactNode }) {
  const stream = useRef<MediaStream | null>(null)
  const recorders = useRef<MediaRecorder[]>([])
  const timers = useRef<number[]>([])
  const replay = useRef('')
  const mounted = useRef(true)
  const pending = useRef(false)
  const [phase, setPhase] = useState<Phase>('opening')
  const [audioOnly, setAudioOnly] = useState(false)
  const [remaining, setRemaining] = useState(LIMIT_SECONDS)
  const [answer, setAnswer] = useState<{ blob: Blob; key: string; replayUrl: string; hasVideo: boolean } | null>(null)
  const [error, setError] = useState('')
  function release() {
    stream.current?.getTracks().forEach((track) => track.stop()); stream.current = null
  }
  function discard() {
    if (replay.current) URL.revokeObjectURL(replay.current)
    replay.current = ''; setAnswer(null)
  }
  async function open() {
    if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') throw new Error('Enregistrement non pris en charge par ce navigateur.')
    const capture = await openCapture((constraints) => navigator.mediaDevices.getUserMedia(constraints))
    // A second open (StrictMode remount, double click) or an unmount keeps a single live capture.
    if (!mounted.current || stream.current) { capture.stream.getTracks().forEach((track) => track.stop()); return stream.current }
    stream.current = capture.stream; setAudioOnly(capture.audioOnly); return capture.stream
  }
  useEffect(() => {
    mounted.current = true
    void open().then((input) => { if (input && mounted.current) setPhase('preview') })
      .catch((cause: unknown) => { if (mounted.current) { setError(cause instanceof Error ? cause.message : 'Accès au microphone refusé'); setPhase('blocked') } })
    return () => {
      mounted.current = false
      timers.current.forEach(clearTimeout) // clears intervals too: timers share one id pool
      stop() // its onstop resolves start(), which then releases the capture and returns
      release()
      if (replay.current) URL.revokeObjectURL(replay.current)
    }
  }, [])
  function stop() {
    recorders.current.forEach((item) => { if (item.state === 'recording') item.stop() })
  }
  async function start() {
    if (pending.current || busy) return
    pending.current = true; setError(''); discard()
    try {
      const input = stream.current ?? await open()
      if (!input) return
      const audioMime = recordingMimeType((value) => MediaRecorder.isTypeSupported(value))
      if (!audioMime) throw new Error('Aucun format audio pris en charge.')
      const videoMime = input.getVideoTracks().length ? reviewMimeType((value) => MediaRecorder.isTypeSupported(value)) : null
      // Upload recording: audio tracks only. Review recording: camera and microphone, kept in memory.
      const upload = new MediaRecorder(new MediaStream(input.getAudioTracks()), { mimeType: audioMime })
      let review: MediaRecorder | null = null
      try { if (videoMime) review = new MediaRecorder(input, { mimeType: videoMime }) } catch { /* replay falls back to the audio answer */ }
      recorders.current = review ? [upload, review] : [upload]
      let size = 0; let failure = ''
      // The review recording is bounded by the three-minute cap; only the uploaded audio has the 25 MiB limit.
      const collect = (item: MediaRecorder, mime: string, limitBytes: number) => new Promise<Blob>((resolve) => {
        const chunks: Blob[] = []
        item.ondataavailable = (event) => {
          if (limitBytes && (size += event.data.size) > limitBytes) { failure = 'La réponse dépasse 25 Mio. Enregistrez une réponse plus courte.'; stop() } else chunks.push(event.data)
        }
        item.onstop = () => resolve(new Blob(chunks, { type: mime }))
        item.onerror = () => { failure = 'Enregistrement interrompu. Veuillez réenregistrer.'; stop() }
      })
      const done = Promise.all([collect(upload, audioMime, 25 * 1024 * 1024), review && videoMime ? collect(review, videoMime, 0) : null])
      recorders.current.forEach((item) => item.start(1000))
      const started = Date.now()
      setRemaining(LIMIT_SECONDS); setPhase('recording')
      timers.current = [
        window.setTimeout(stop, LIMIT_SECONDS * 1000),
        window.setInterval(() => setRemaining(Math.max(0, LIMIT_SECONDS - Math.floor((Date.now() - started) / 1000))), 500),
      ]
      const [audio, video] = await done
      timers.current.forEach(clearTimeout); release()
      if (!mounted.current) return
      if (failure) { setError(failure); setPhase('blocked'); return }
      replay.current = URL.createObjectURL(video ?? audio)
      setAnswer({ blob: audio, key: crypto.randomUUID(), replayUrl: replay.current, hasVideo: !!video }); setPhase('review')
    } catch (cause) {
      stop(); release()
      if (mounted.current) { setError(cause instanceof Error ? cause.message : 'Accès au microphone refusé'); setPhase('blocked') }
    } finally { pending.current = false }
  }
  async function submit() {
    if (!answer) return
    // On success the page moves to analysis and unmounts this recorder, which revokes the replay URL.
    try { await onSubmit(answer.blob, answer.key) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Envoi interrompu. Réessayez avec la même réponse.') }
  }
  const showPreview = (phase === 'preview' || phase === 'recording') && !audioOnly
  const candidate = <>
    <div className="relative">
      {/* Distinct keys: a reused preview element keeps the stopped camera as srcObject, which wins over src and shows black. */}
      {answer?.hasVideo ? <video key="replay" src={answer.replayUrl} aria-label="Revoir votre réponse" className={`${STAGE_FRAME} w-full object-contain`} controls playsInline />
        : showPreview ? <video key="preview" ref={(element) => { if (element && element.srcObject !== stream.current) element.srcObject = stream.current }} aria-label="Aperçu de votre caméra" className={`${STAGE_FRAME} w-full -scale-x-100`} autoPlay muted playsInline />
        : <CameraIdle>{audioOnly ? 'Réponse en audio seulement' : 'Caméra inactive'}</CameraIdle>}
      {phase === 'recording' && <p className="absolute left-3 top-3 flex items-center gap-2 rounded-full bg-coral px-3 py-1 text-sm font-medium text-white">
        <span aria-hidden="true" className="h-2 w-2 rounded-full bg-white" />Enregistrement <span role="timer" aria-label={`Temps restant ${formatCountdown(remaining)}`}>{formatCountdown(remaining)}</span>
      </p>}
    </div>
    {answer && !answer.hasVideo && <audio src={answer.replayUrl} aria-label="Revoir votre réponse" controls />}
    {/* The timer itself is silent to screen readers; the status announces the last minute once. */}
    <p role="status">{STATUS[phase === 'recording' && remaining <= 60 ? 'lastMinute' : phase]} · 3 minutes maximum</p>
    {audioOnly && <p className="text-sm text-slate">Caméra indisponible ou refusée : votre réponse est enregistrée en audio seulement.</p>}
    <p className="text-sm text-slate">Seul l’audio est envoyé ; la vidéo reste sur votre appareil.</p>
    {error && <p role="alert" className="text-coral">{error}</p>}
  </>
  const actions = <>
    {phase === 'recording' ? <Button onClick={stop}>Arrêter l’enregistrement</Button>
      : answer ? <>
        <Button disabled={busy} onClick={() => void submit()}>{busy ? 'Envoi…' : 'Envoyer la réponse'}</Button>
        <Button variant="secondaire" disabled={busy} onClick={() => void start()}>Réenregistrer</Button>
      </>
      : <Button disabled={busy || phase === 'opening'} onClick={() => void start()}>Démarrer l’enregistrement</Button>}
    {cancel}
  </>
  return <InterviewStage interviewer={interviewer} candidate={candidate} actions={actions} />
}
