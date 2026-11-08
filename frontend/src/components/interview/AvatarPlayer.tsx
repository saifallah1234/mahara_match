import { useEffect, useRef, useState } from 'react'
import { requestBlob } from '../../api/client'
import type { Playback } from '../../api/mockInterviews'
import { Button } from '../ui'

export function AvatarPlayer({ playback, onDone, loop = false, className = 'max-h-80 w-full rounded-lg bg-navy' }: { playback: Playback; onDone?: () => void; loop?: boolean; className?: string }) {
  const [urls, setUrls] = useState<{ video: string; audio?: string; generated: boolean } | null>(null)
  const [fallback, setFallback] = useState(false)
  const [error, setError] = useState('')
  const video = useRef<HTMLVideoElement>(null)
  const audio = useRef<HTMLAudioElement>(null)
  const videoPath = !fallback && playback.video || playback.avatar
  const audioPath = !fallback && playback.video ? null : playback.audio
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches
  useEffect(() => {
    let disposed = false
    const created: string[] = []
    setUrls(null); setError('')
    async function load() {
      if (!videoPath) throw new Error('Vidéo indisponible')
      let generated = !!playback.video && !fallback
      let blobs: [Blob, Blob | null]
      try {
        blobs = await Promise.all([requestBlob(videoPath), audioPath ? requestBlob(audioPath) : Promise.resolve(null)])
      } catch (cause) {
        if (!generated || !playback.avatar || !playback.audio) throw cause
        blobs = await Promise.all([requestBlob(playback.avatar), requestBlob(playback.audio)])
        generated = false
      }
      if (disposed) return
      const videoURL = URL.createObjectURL(blobs[0]); created.push(videoURL)
      const audioURL = blobs[1] ? URL.createObjectURL(blobs[1]) : undefined
      if (audioURL) created.push(audioURL)
      setUrls({ video: videoURL, audio: audioURL, generated })
    }
    void load().catch((cause: unknown) => { if (!disposed) setError(cause instanceof Error ? cause.message : 'Lecture indisponible') })
    return () => { disposed = true; created.forEach((url) => URL.revokeObjectURL(url)) }
  }, [videoPath, audioPath, playback.avatar, playback.audio, playback.video, fallback])
  useEffect(() => {
    if (urls && loop && !reducedMotion) void video.current?.play().catch(() => setError('Cliquez sur Lire pour lancer l’animation.'))
  }, [urls, loop, reducedMotion])
  async function play() {
    setError('')
    try {
      if (video.current) {
        video.current.currentTime = 0
        if (!reducedMotion || urls?.generated) await video.current.play()
      }
      if (audio.current) { audio.current.currentTime = 0; await audio.current.play() }
    } catch { setError('La lecture a été interrompue. Cliquez sur Lire pour réessayer.') }
  }
  return <div className="space-y-2">
    {urls ? <>
      <video ref={video} src={urls.video} className={className} muted={!urls.generated} playsInline loop={loop && !reducedMotion} controls={urls.generated} onEnded={urls.generated ? onDone : undefined} onError={() => setError('Vidéo indisponible')} />
      {urls.audio && <audio ref={audio} src={urls.audio} controls onEnded={() => { video.current?.pause(); onDone?.() }} onError={() => setError('Audio indisponible')} />}
      <Button onClick={() => void play()}>Lire</Button>
    </> : <p role="status">Chargement de la vidéo…</p>}
    {(playback.lip_synced === false || urls && !urls.generated && !!urls.audio) && <p className="text-xs text-slate">Cette vidéo utilise une voix séparée, sans synchronisation des lèvres.</p>}
    {error && urls?.generated && playback.avatar && playback.audio && <Button onClick={() => setFallback(true)}>Utiliser la voix avec l’avatar</Button>}
    {error && <p role="alert" className="text-coral">{error}</p>}
  </div>
}
