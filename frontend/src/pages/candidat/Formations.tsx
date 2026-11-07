import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Field, Panel, Select, Tabs } from '../../components/ui'
import { useCandidateTraining } from '../../state/candidateTraining'
import { ENROLLMENT_STATUS_LABEL, formatDate, formatPrice, labelFor } from '../../lib/format'

type Tab = 'catalogue' | 'mine'
const delivery: Record<string, string> = { ONLINE: 'À distance', PRESENTIAL: 'Présentiel', HYBRID: 'Hybride' }
const level: Record<string, string> = { BEGINNER: 'Débutant', INTERMEDIATE: 'Intermédiaire', ADVANCED: 'Avancé' }
export default function CandidatFormations() {
  const { programs, sessions, enrollments, loading, error, enroll, cancelEnrollment } = useCandidateTraining()
  const [tab, setTab] = useState<Tab>('catalogue')
  const [mode, setMode] = useState('')
  const [busy, setBusy] = useState('')
  const [cancelling, setCancelling] = useState<(typeof enrollments)[number] | null>(null)
  async function action(id: string, work: () => Promise<void>) { setBusy(id); try { await work() } catch { /* The workspace shows the API error. */ } finally { setBusy('') } }
  const catalogue = programs.filter((program) => program.status === 'ACTIVE' && (!mode || program.delivery_mode === mode))
  return <>
    <PageHeader title="Formations" />
    <PageBody className="space-y-5">
      {error && <p role="alert" className="text-coral">{error}</p>}
      {loading && <p className="text-slate">Chargement…</p>}
      <Tabs<Tab> active={tab} onChange={setTab} tabs={[{ id: 'catalogue', label: 'Catalogue', count: catalogue.length }, { id: 'mine', label: 'Mes inscriptions', count: enrollments.length }]} />
      {tab === 'catalogue' && <><Panel><div className="max-w-xs p-5"><Field label="Modalité"><Select value={mode} onChange={(event) => setMode(event.target.value)}><option value="">Toutes</option>{Object.entries(delivery).map(([value, label]) => <option key={value} value={value}>{label}</option>)}</Select></Field></div></Panel>
        {!catalogue.length && <Panel><EmptyState title="Aucune formation publiée" /></Panel>}
        {catalogue.map((program) => <Panel key={program.id} title={program.title} description={`${program.organization_name} · ${delivery[program.delivery_mode] ?? program.delivery_mode} · ${level[program.level] ?? program.level}`}>
          <div className="space-y-3 p-5 text-sm"><p className="text-navy">{program.description}</p><p className="text-slate">{formatPrice(program.price)}</p></div>
          <ul className="divide-y divide-line">{sessions.filter((session) => session.program === program.id).map((session) => {
            const existing = enrollments.find((item) => item.session === session.id)
            const open = ['PLANNED', 'ONGOING'].includes(session.status) && new Date(session.registration_deadline) >= new Date()
            return <li key={session.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3 text-sm"><div><p>Du {formatDate(session.start_date)} au {formatDate(session.end_date)}</p><p className="text-slate">{session.location_or_url} · inscription avant le {formatDate(session.registration_deadline)}</p></div>{existing ? <Badge tone={existing.status === 'DROPPED' ? 'neutre' : 'positif'}>{existing.status === 'DROPPED' ? 'Annulée' : 'Inscrit'}</Badge> : <Button size="sm" disabled={!open || busy === session.id} onClick={() => void action(session.id, () => enroll(session.id))}>{open ? 'S’inscrire' : 'Inscriptions fermées'}</Button>}</li>
          })}</ul>
        </Panel>)}
      </>}
      {tab === 'mine' && <Panel title="Mes inscriptions">{!enrollments.length ? <EmptyState title="Aucune inscription" /> : <ul className="divide-y divide-line">{enrollments.map((item) => {
        return <li key={item.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4 text-sm"><div><p className="font-medium text-navy">{item.program_title}</p><p className="text-slate">{formatDate(item.session_start_date)} · {labelFor(ENROLLMENT_STATUS_LABEL, item.status)}</p></div><Button size="sm" variant="danger" disabled={busy === item.id || ['COMPLETED', 'DROPPED'].includes(item.status)} onClick={() => setCancelling(item)}>Annuler</Button></li>
      })}</ul>}</Panel>}
      {cancelling && (
        <ConfirmDialog
          title="Annuler mon inscription ?"
          danger
          onCancel={() => setCancelling(null)}
          onConfirm={() => { void action(cancelling.id, () => cancelEnrollment(cancelling.id)); setCancelling(null) }}
        >
          Votre inscription sera annulée.
        </ConfirmDialog>
      )}
    </PageBody>
  </>
}
