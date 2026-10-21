import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Field, Input, Panel, Select } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel, type RecruiterInterview } from '../../api/recruiter'
import { INTERVIEW_STATUS_LABEL, INTERVIEW_TYPE_LABEL, formatDateTime, labelFor } from '../../lib/format'

const STATUS_TONE = { SCHEDULED: 'encours', COMPLETED: 'positif', CANCELLED: 'negatif' } as const
const ACTIVE = ['SUBMITTED', 'UNDER_REVIEW', 'PRESELECTED', 'INTERVIEW']

export default function RecruteurEntretiens() {
  const { interviews, applications, error, scheduleInterview, setInterviewStatus } = useRecruiter()
  const [form, setForm] = useState({ application_id: '', type: 'VIDEO', scheduled_at: '', duration_minutes: '45', location_or_url: '' })
  const [busy, setBusy] = useState(false)
  const [cancelling, setCancelling] = useState<RecruiterInterview | null>(null)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  const candidates = applications.filter((a) => ACTIVE.includes(a.status))
  const sorted = [...interviews].sort((a, b) => +new Date(a.scheduled_at) - +new Date(b.scheduled_at))
  const upcoming = sorted.filter((i) => i.status === 'SCHEDULED')
  const past = sorted.filter((i) => i.status !== 'SCHEDULED')
  const who = (i: RecruiterInterview) => {
    const a = applications.find((x) => x.id === i.application_id)
    return a ? `${candidateLabel(a)} — ${a.offer_title}` : 'Candidature'
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
              {formatDateTime(i.scheduled_at)} · {i.duration_minutes} min · {labelFor(INTERVIEW_TYPE_LABEL, i.type)}
              {i.location_or_url && ` · ${i.location_or_url}`}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Badge tone={STATUS_TONE[i.status]}>{labelFor(INTERVIEW_STATUS_LABEL, i.status)}</Badge>
            {actions && (
              <>
                <Button size="sm" onClick={() => void setInterviewStatus(i.id, 'COMPLETED').catch(() => {})}>Réalisé</Button>
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
              <Button disabled={busy || !form.application_id || !form.scheduled_at} onClick={() => void submit()}>Planifier</Button>
            </div>
          </div>
        </Panel>

        <Panel title={`À venir (${upcoming.length})`}>
          {upcoming.length === 0 ? <EmptyState title="Aucun entretien planifié" /> : list(upcoming, true)}
        </Panel>
        {past.length > 0 && <Panel title="Historique">{list(past, false)}</Panel>}
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