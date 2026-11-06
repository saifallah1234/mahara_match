import { useEffect, useRef, useState } from 'react'
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom'
import { answerInterview, createInterview, getInterview, getInterviewFeedback, interviewAction, interviewHistory, type InterviewFeedback, type InterviewSession } from '../../api/mockInterviews'
import { AvatarPlayer } from '../../components/interview/AvatarPlayer'
import { AnswerRecorder } from '../../components/interview/AnswerRecorder'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, ConfirmDialog, Field, Panel, Select } from '../../components/ui'
import { interviewDisplayState, type InterviewDisplayState } from '../../lib/mockInterviewMachine'
import { MOCK_INTERVIEW_LABEL, MOCK_JOB_STAGE_LABEL, MOCK_JOB_STATUS_LABEL, formatDateTime, labelFor } from '../../lib/format'
import { useCandidate } from '../../state/candidate'

export default function MockInterview() {
  const { sessionId } = useParams()
  const [search] = useSearchParams()
  const navigate = useNavigate()
  const { cvs } = useCandidate()
  const [cvId, setCvId] = useState('')
  const [session, setSession] = useState<InterviewSession | null>(null)
  const snapshot = useRef<InterviewSession | null>(null)
  const [display, setDisplay] = useState<InterviewDisplayState>('PREPARING')
  const [history, setHistory] = useState<InterviewSession[]>([])
  const [page, setPage] = useState(1)
  const [hasNext, setHasNext] = useState(false)
  const [feedback, setFeedback] = useState<InterviewFeedback | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [confirmingCancel, setConfirmingCancel] = useState(false)
  const creation = useRef({ input: '', key: crypto.randomUUID() })
  const offerId = search.get('offer') || ''
  function update(value: InterviewSession) {
    const old = snapshot.current
    if (old?.current_turn_id === value.current_turn_id && old.status === 'IN_PROGRESS' && value.status === 'IN_PROGRESS') {
      value = { ...value, playback: { ...value.playback, turn: old.playback.turn } }
    }
    if (!old || old.status !== value.status || old.current_turn_id !== value.current_turn_id) setDisplay(interviewDisplayState(value.status))
    snapshot.current = value; setSession(value)
  }
  useEffect(() => {
    let active = true; let timer: ReturnType<typeof setTimeout>
    snapshot.current = null; setSession(null); setFeedback(null); setError('')
    async function poll() {
      try {
        if (sessionId) {
          const value = await getInterview(sessionId)
          if (!active) return
          update(value)
          if (value.status === 'COMPLETED') setFeedback(await getInterviewFeedback(sessionId))
          if (!['COMPLETED', 'CANCELLED'].includes(value.status)) timer = setTimeout(() => void poll(), 2000)
        } else {
          const value = await interviewHistory(page)
          if (active) { setHistory(value.results); setHasNext(!!value.next) }
        }
      } catch (cause) {
        if (active) { setError(cause instanceof Error ? cause.message : 'Chargement impossible'); if (sessionId) timer = setTimeout(() => void poll(), 4000) }
      }
    }
    void poll()
    return () => { active = false; clearTimeout(timer) }
  }, [sessionId, page])
  async function create() {
    setBusy(true); setError('')
    const input = `${offerId}/${cvId}`
    if (creation.current.input !== input) creation.current = { input, key: crypto.randomUUID() }
    try { const value = await createInterview(offerId, cvId, creation.current.key); navigate(`/candidat/entretiens-blancs/${value.id}`) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Préparation impossible') }
    finally { setBusy(false) }
  }
  async function action(name: 'start' | 'retry' | 'cancel') {
    if (!session) return
    setBusy(true); setError('')
    try { update(await interviewAction(session.id, name)); if (name === 'start') setDisplay('INTRO') }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'Action impossible') }
    finally { setBusy(false) }
  }
  async function submit(blob: Blob, key: string) {
    if (!session?.current_turn_id) return
    setBusy(true); setDisplay('UPLOADING')
    try { update(await answerInterview(session, session.current_turn_id, blob, key)) }
    catch (cause) { setDisplay('LISTENING'); throw cause }
    finally { setBusy(false) }
  }
  const turn = session?.turns.find((item) => item.id === session.current_turn_id)
  return <>
    <PageHeader title="Entretien blanc" description="Trois questions et au maximum une relance. En français." />
    <PageBody className="space-y-5">
      {error && <p role="alert" className="text-coral">{error}</p>}
      {!sessionId ? <>
        {offerId && <Panel title="Préparer un entretien"><div className="space-y-3 p-5">
          <Field label="CV facultatif"><Select value={cvId} onChange={(event) => setCvId(event.target.value)}><option value="">Utiliser mon profil</option>{cvs.map((cv) => <option key={cv.id} value={cv.id}>{cv.title}</option>)}</Select></Field>
          <Button disabled={busy} onClick={() => void create()}>Préparer l’entretien</Button>
        </div></Panel>}
        <Panel title="Mes entretiens"><ul className="space-y-2 p-5">{history.map((item) => <li key={item.id}><Link className="text-teal underline" to={`/candidat/entretiens-blancs/${item.id}`}>{item.offer_title && `${item.offer_title} · `}{MOCK_INTERVIEW_LABEL[item.status] ?? 'Entretien'} · {formatDateTime(item.created_at)}</Link></li>)}</ul><div className="flex gap-2 p-5"><Button disabled={page <= 1} onClick={() => setPage(page - 1)}>Précédent</Button><Button disabled={!hasNext} onClick={() => setPage(page + 1)}>Suivant</Button></div></Panel>
      </> : session ? <>
        {session.availability.simulated && <p role="status" className="rounded-lg bg-amber/10 p-3">Mode simulé : tonalités audio, transcription prédéfinie et vidéos sans lip-sync réel.</p>}
        <p role="status">État : {MOCK_INTERVIEW_LABEL[display]}</p>
        {['PREPARING', 'THINKING', 'FAILED'].includes(display) && <Panel title="Traitements"><ul className="p-5">{session.jobs.map((job) => <li key={job.id}>{labelFor(MOCK_JOB_STAGE_LABEL, job.stage)} : {labelFor(MOCK_JOB_STATUS_LABEL, job.status)}{job.error_code && ` (${job.error_code})`}</li>)}</ul></Panel>}
        {display === 'READY' && <Button disabled={busy} onClick={() => void action('start')}>Commencer</Button>}
        {display === 'INTRO' && <AvatarPlayer playback={{ video: session.playback.introduction }} onDone={() => setDisplay('SPEAKING')} />}
        {turn && <Panel title={turn.kind === 'FOLLOWUP' ? 'Relance' : `Question ${turn.position}/3`}><p className="p-5">{turn.question}</p></Panel>}
        {display === 'SPEAKING' && session.playback.turn && <AvatarPlayer key={turn?.id} playback={session.playback.turn} onDone={() => setDisplay('LISTENING')} />}
        {display === 'THINKING' && <AvatarPlayer playback={{ avatar: session.playback.thinking_avatar }} loop />}
        {(display === 'LISTENING' || display === 'UPLOADING') && <>
          <AvatarPlayer playback={{ avatar: session.playback.listening_avatar }} loop />
          <AnswerRecorder key={turn?.id} busy={busy} onSubmit={submit} />
        </>}
        {display === 'FAILED' && <Button disabled={busy} onClick={() => void action('retry')}>Réessayer le traitement</Button>}
        {session.allowed_actions.includes('cancel') && <Button disabled={busy} onClick={() => setConfirmingCancel(true)}>Annuler l’entretien</Button>}
        {display === 'COMPLETED' && <>
          {session.playback.closing_audio && <AvatarPlayer playback={{ audio: session.playback.closing_audio, avatar: session.playback.neutral_avatar }} />}
          {feedback && <Panel title="Votre retour"><div className="space-y-4 p-5"><p>{feedback.summary}</p>{feedback.questions.map((row, index) => <section key={row.turn_id}><h2 className="font-semibold">Réponse {index + 1}</h2><p>Points forts : {row.strengths.join(' ')}</p><p>À approfondir : {row.gaps.join(' ')}</p>{row.excerpts.map((quote) => <blockquote key={quote}>« {quote} »</blockquote>)}<p>Pour progresser : {row.improvements.join(' ')}</p></section>)}</div></Panel>}
        </>}
      </> : <p role="status">Chargement…</p>}
      {confirmingCancel && (
        <ConfirmDialog
          title="Annuler l’entretien blanc ?"
          danger
          onCancel={() => setConfirmingCancel(false)}
          onConfirm={() => { setConfirmingCancel(false); void action('cancel') }}
        >
          L’entretien en cours sera annulé.
        </ConfirmDialog>
      )}
    </PageBody>
  </>
}
