import { useEffect, useRef, useState } from 'react'
import { recordingMimeType } from '../../lib/mockInterviewMachine'
import { Button } from '../ui'

export function AnswerRecorder({ onSubmit, busy }: { onSubmit: (blob: Blob, key: string) => Promise<void>; busy: boolean }) {
  const recorder = useRef<MediaRecorder | null>(null)
  const stream = useRef<MediaStream | null>(null)
  const timer = useRef<ReturnType<typeof setTimeout>>()
  const mounted = useRef(true)
  const [recording, setRecording] = useState(false)
  const [answer, setAnswer] = useState<{ blob: Blob; key: string } | null>(null)
  const [error, setError] = useState('')
  const pending = useRef(false)
  useEffect(() => {
    mounted.current = true
    return () => {
    mounted.current = false
    clearTimeout(timer.current)
    if (recorder.current) { recorder.current.onstop = null; if (recorder.current.state === 'recording') recorder.current.stop() }
    stream.current?.getTracks().forEach((track) => track.stop())
    }
  }, [])
  async function start() {
    if (pending.current || busy) return
    pending.current = true; setError(''); setAnswer(null)
    try {
      if (!navigator.mediaDevices?.getUserMedia || typeof MediaRecorder === 'undefined') throw new Error('Enregistrement audio non pris en charge par ce navigateur.')
      const mime = recordingMimeType((value) => MediaRecorder.isTypeSupported(value))
      if (!mime) throw new Error('Aucun format audio pris en charge.')
      const input = await navigator.mediaDevices.getUserMedia({ audio: true })
      if (!mounted.current) { input.getTracks().forEach((track) => track.stop()); return }
      stream.current = input
      const instance = new MediaRecorder(input, { mimeType: mime }); recorder.current = instance
      const chunks: Blob[] = []; let size = 0; let oversized = false
      instance.ondataavailable = (event) => {
        size += event.data.size
        if (size > 25 * 1024 * 1024) { oversized = true; if (instance.state === 'recording') instance.stop() }
        else chunks.push(event.data)
      }
      instance.onstop = () => {
        clearTimeout(timer.current); input.getTracks().forEach((track) => track.stop()); setRecording(false)
        if (oversized) setError('La réponse dépasse 25 Mio. Enregistrez une réponse plus courte.')
        else setAnswer({ blob: new Blob(chunks, { type: mime }), key: crypto.randomUUID() })
      }
      instance.onerror = () => { setError('Enregistrement interrompu. Veuillez réenregistrer.'); instance.stop() }
      instance.start(1000); setRecording(true)
      timer.current = setTimeout(() => { if (instance.state === 'recording') instance.stop() }, 180000)
    } catch (cause) { setError(cause instanceof Error ? cause.message : 'Accès au microphone refusé'); stream.current?.getTracks().forEach((track) => track.stop()) }
    finally { pending.current = false }
  }
  async function submit() {
    if (!answer) return
    try { await onSubmit(answer.blob, answer.key) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Envoi interrompu. Réessayez avec la même réponse.') }
  }
  return <div className="space-y-3">
    <p role="status">{recording ? 'Microphone actif — enregistrement en cours' : 'Microphone arrêté'} · 3 minutes maximum</p>
    <div className="flex gap-3">
      {recording ? <Button onClick={() => recorder.current?.stop()}>Arrêter l’enregistrement</Button> : <Button disabled={busy} onClick={() => void start()}>{answer ? 'Réenregistrer' : 'Démarrer l’enregistrement'}</Button>}
      {answer && <Button disabled={busy} onClick={() => void submit()}>{busy ? 'Envoi…' : 'Envoyer la réponse'}</Button>}
    </div>
    {error && <p role="alert" className="text-coral">{error}</p>}
  </div>
}
