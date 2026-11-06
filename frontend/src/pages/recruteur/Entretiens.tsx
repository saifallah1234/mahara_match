import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Field, Input, Panel, Select } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel, type RecruiterInterview } from '../../api/recruiter'
import { INTERVIEW_STATUS_LABEL, INTERVIEW_TYPE_LABEL, formatTunisDateTime, labelFor } from '../../lib/format'

const STATUS_TONE = { SCHEDULED: 'encours', COMPLETED: 'positif', CANCELLED: 'negatif' } as const
const PRE_INTERVIEW = ['SUBMITTED', 'UNDER_REVIEW', 'PRESELECTED']

export default function RecruteurEntretiens() {
  const { interviews, applications, error, scheduleInterview, setInterviewStatus, moveApplication } = useRecruiter()
  const [form, setForm] = useState({ application_id: '', type: 'VIDEO', scheduled_at: '', duration_minutes: '45', location_or_url: '' })
  const [busy, setBusy] = useState(false)
  const [cancelling, setCancelling] = useState<RecruiterInterview | null>(null)
  const [completing, setCompleting] = useState<RecruiterInterview | null>(null)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  // The backend refuses an interview unless the application is already at INTERVIEW, so earlier stages are offered with a one-click advance.
  const candidates = applications.filter((a) => a.status === 'INTERVIEW' || PRE_INTERVIEW.includes(a.status))
  const picked = applications.find((a) => a.id === form.application_id)
  const sorted = [...interviews].sort((a, b) => +new Date(a.scheduled_at) - +new Date(b.scheduled_at))
  const upcoming = sorted.filter((i) => i.status === 'SCHEDULED')
  const past = sorted.filter((i) => i.status !== 'SCHEDULED')
  const who = (i: RecruiterInterview) => {
    const a = applications.find((x) => x.id === i.application_id)
    return a ? `${candidateLabel(a)} — ${a.offer_title}` : 'Candidature'
  }

  async function advance() {
    if (!picked) return
    setBusy(true)
    try {
      await moveApplication(picked.id, 'INTERVIEW')
    } catch { /* l'erreur s'affiche en haut de la page */ }
    finally { setBusy(false) }
  }

  async function submit() {
    setBusy(true)
    try {
      await scheduleInterview({
        application_id: form.application_id, type: form.type as RecruiterInterview['type'],
        scheduled_at: new Date(form.scheduled_at).toISOString(),
        duration_minutes: Number(form.duration_minutes) || 45, location_or_url: form.location_or_url.trim(),
      })
      setForm({ ...form, application_id: '', scheduled_at: '', location_or_url: '' })
    } catch { /* l'erreur s'affiche en haut de la page */ }
    finally { setBusy(false) }
  }

  const list = (items: RecruiterInterview[], actions: boolean) => (
    <ul className="divide-y divide-line/70">
      {items.map((i) => (
        <li key={i.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
          <div>
            <p className="text-[14px] font-medium text-navy">{who(i)}</p>
            <p className="text-[12.5px] text-slate">
              {formatTunisDateTime(i.scheduled_at)} · {i.duration_minutes} min · {labelFor(INTERVIEW_TYPE_LABEL, i.type)}
              {i.location_or_url && ` · ${i.location_or_url}`}
            </p>
            {i.feedback && <p className="mt-1 text-[12.5px] text-navy">{i.feedback}</p>}
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE[i.status]}>{labelFor(INTERVIEW_STATUS_LABEL, i.status)}</Badge>
            {actions && (
              <>
                <Button size="sm" onClick={() => setCompleting(i)}>Réalisé</Button>
                <Button size="sm" variant="discret" onClick={() => setCancelling(i)}>Annuler</Button>
              </>
            )}
          </div>
        </li>
      ))}
    </ul>
  )

  return (
    <>
      <PageHeader title="Entretiens" />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}

        <Panel title="Planifier un entretien">
          <div className="grid gap-4 p-5 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Field label="Candidature" required>
                <Select value={form.application_id} onChange={set('application_id')}>
                  <option value="">Choisir…</option>
                  {candidates.map((a) => <option key={a.id} value={a.id}>{candidateLabel(a)} — {a.offer_title}</option>)}
                </Select>
              </Field>
              {picked && picked.status !== 'INTERVIEW' && (
                <div className="mt-2 flex flex-wrap items-center gap-3">
                  <p className="text-[12.5px] text-slate">Une candidature doit être au statut Entretien avant d’être planifiée.</p>
                  <Button size="sm" variant="secondaire" disabled={busy} onClick={() => void advance()}>Passer la candidature au statut Entretien</Button>
                </div>
              )}
              <p className="mt-1.5 text-[12.5px] text-slate">
                Vous pouvez aussi la faire avancer depuis le <Link to="/recruteur/candidatures" className="text-teal hover:underline">Suivi des candidatures</Link>.
              </p>
            </div>
            <Field label="Type">
              <Select value={form.type} onChange={set('type')}>
                {Object.entries(INTERVIEW_TYPE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </Select>
            </Field>
            <Field label="Date et heure" required><Input type="datetime-local" value={form.scheduled_at} onChange={set('scheduled_at')} /></Field>
            <Field label="Durée (minutes)"><Input type="number" value={form.duration_minutes} onChange={set('duration_minutes')} /></Field>
            <Field label="Lieu ou lien"><Input value={form.location_or_url} onChange={set('location_or_url')} /></Field>
            <div className="sm:col-span-2">
              <Button disabled={busy || picked?.status !== 'INTERVIEW' || !form.scheduled_at} onClick={() => void submit()}>Planifier</Button>
            </div>
          </div>
        </Panel>

        <Panel title={`À venir (${upcoming.length})`}>
          {upcoming.length === 0 ? <EmptyState title="Aucun entretien planifié" /> : list(upcoming, true)}
        </Panel>
        {past.length > 0 && <Panel title="Historique">{list(past, false)}</Panel>}
        {completing && (
          <ConfirmDialog
            title="Marquer cet entretien comme réalisé ?"
            reasonLabel="Compte rendu (facultatif)"
            onCancel={() => setCompleting(null)}
            onConfirm={(feedback) => { void setInterviewStatus(completing.id, 'COMPLETED', feedback || undefined).catch(() => {}); setCompleting(null) }}
          >
            L’entretien avec {who(completing)} sera enregistré comme réalisé.
          </ConfirmDialog>
        )}
        {cancelling && (
          <ConfirmDialog
            title="Annuler cet entretien ?"
            danger
            onCancel={() => setCancelling(null)}
            onConfirm={() => { void setInterviewStatus(cancelling.id, 'CANCELLED').catch(() => {}); setCancelling(null) }}
          >
            L’entretien avec {who(cancelling)} sera annulé.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}