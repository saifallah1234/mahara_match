import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Panel, Tabs } from '../../components/ui'
import { useCandidate } from '../../state/candidate'
import { downloadPath } from '../../api/candidate'
import { INTERVIEW_STATUS_LABEL, INTERVIEW_TYPE_LABEL, formatDate, formatDateTime, labelFor } from '../../lib/format'
import { STATUS_LABEL } from '../../lib/statusMachine'
import type { ApplicationStatus } from '../../lib/types'

type Tab = 'active' | 'closed'
const closed = ['REJECTED', 'WITHDRAWN', 'HIRED']
export default function CandidatCandidatures() {
  const { applications, interviews, history, withdraw, cvs } = useCandidate()
  const [tab, setTab] = useState<Tab>('active')
  const [busy, setBusy] = useState('')
  const [downloadError, setDownloadError] = useState('')
  const [withdrawing, setWithdrawing] = useState<(typeof applications)[number] | null>(null)
  const active = applications.filter((item) => !closed.includes(item.status))
  const done = applications.filter((item) => closed.includes(item.status))
  const shown = [...(tab === 'active' ? active : done)].sort((a, b) => b.applied_at.localeCompare(a.applied_at))
  async function remove(id: string) {
    setBusy(id)
    try { await withdraw(id) } catch { /* The workspace shows the API error. */ }
    finally { setBusy('') }
  }
  return <>
    <PageHeader title="Mes candidatures" />
    <PageBody className="space-y-5">
      {downloadError && <p role="alert" className="text-coral">{downloadError}</p>}
      <Tabs<Tab> active={tab} onChange={setTab} tabs={[{ id: 'active', label: 'En cours', count: active.length }, { id: 'closed', label: 'Clôturées', count: done.length }]} />
      {!shown.length && <Panel><EmptyState title="Aucune candidature dans cette catégorie" action={<Link to="/candidat/offres"><Button>Voir les offres</Button></Link>} /></Panel>}
      {shown.map((item) => <Panel key={item.id} title={item.offer_title} action={<Badge tone={closed.includes(item.status) ? 'neutre' : 'encours'}>{STATUS_LABEL[item.status as ApplicationStatus] ?? item.status}</Badge>}>
        <div className="space-y-3 p-5 text-sm">
          <p className="text-slate">Déposée le {formatDate(item.applied_at)} · CV {cvs.find((cv) => cv.id === item.cv_id)?.title ?? 'transmis'}</p>
          {(!closed.includes(item.status) || cvs.some((cv) => cv.id === item.cv_id)) && <Button size="sm" variant="secondaire" onClick={() => void downloadPath(`/applications/${item.id}/cv/`, 'CV-transmis').catch((failure) => setDownloadError(failure instanceof Error ? failure.message : 'Téléchargement impossible.'))}>Télécharger le CV transmis</Button>}
          {item.cover_letter && <p className="whitespace-pre-wrap text-navy">{item.cover_letter}</p>}
          {interviews.filter((interview) => interview.application_id === item.id).map((interview) => <p key={interview.id} className="text-navy">Entretien · {labelFor(INTERVIEW_TYPE_LABEL, interview.type)} · {formatDateTime(interview.scheduled_at)} · {interview.location_or_url} · {labelFor(INTERVIEW_STATUS_LABEL, interview.status)}</p>)}
          <div><p className="font-medium text-navy">Historique</p><ul className="mt-1 space-y-1 text-slate">{history.filter((entry) => entry.application_id === item.id).map((entry) => <li key={entry.id}>{formatDateTime(entry.changed_at)} · {STATUS_LABEL[entry.status as ApplicationStatus] ?? entry.status}</li>)}</ul></div>
          {!closed.includes(item.status) && <Button variant="danger" size="sm" disabled={busy === item.id} onClick={() => setWithdrawing(item)}>Retirer ma candidature</Button>}
        </div>
      </Panel>)}
      {withdrawing && (
        <ConfirmDialog
          title="Retirer ma candidature ?"
          danger
          onCancel={() => setWithdrawing(null)}
          onConfirm={() => { void remove(withdrawing.id); setWithdrawing(null) }}
        >
          Votre candidature à « {withdrawing.offer_title} » sera retirée.
        </ConfirmDialog>
      )}
    </PageBody>
  </>
}
