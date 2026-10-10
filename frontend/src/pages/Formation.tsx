import { useState } from 'react'
import { PageBody, PageHeader } from '../components/layout'
import { Badge, Button, Cell, EmptyState, Field, Input, Panel, Row, Select, StatTile, Table, Textarea } from '../components/ui'
import { useAuth } from '../state/auth'
import { useTraining } from '../state/training'
import { formatDate } from '../lib/format'
import type { Program, ProgramInput } from '../api/training'

const MODE = { ONLINE: 'En ligne', PRESENTIAL: 'Présentiel', HYBRID: 'Hybride' } as const
const LEVEL = { BEGINNER: 'Débutant', INTERMEDIATE: 'Intermédiaire', ADVANCED: 'Avancé' } as const
const PSTATUS = { DRAFT: 'Brouillon', ACTIVE: 'Actif', ARCHIVED: 'Archivé' } as const
const SSTATUS = { PLANNED: 'Planifiée', ONGOING: 'En cours', COMPLETED: 'Terminée', CANCELLED: 'Annulée' } as const
const price = (p: Program) => (p.is_free ? 'Gratuit' : `${p.price} TND`)
const ENROLL = { REGISTERED: 'Inscrit', IN_PROGRESS: 'En cours', COMPLETED: 'Terminé', DROPPED: 'Abandonné' } as const

export function FormationDashboard() {
  const { workspace } = useAuth()
  const { programs, sessions, enrollments, loading, error } = useTraining()
  return (
    <>
      <PageHeader title={workspace?.organization?.legal_name ?? 'Espace formation'} />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {loading && <p className="text-slate">Chargement…</p>}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={programs.filter((p) => p.status === 'ACTIVE').length} label="Programmes actifs" note={`${programs.length} au total`} />
          <StatTile value={sessions.filter((s) => s.status === 'PLANNED').length} label="Sessions planifiées" tone="teal" />
          <StatTile value={sessions.filter((s) => s.status === 'ONGOING').length} label="Sessions en cours" tone="leaf" />
          <StatTile value={enrollments.length} label="Inscriptions" tone="coral" />
        </div>
      </PageBody>
    </>
  )
}

export function FormationProgrammes() {
  const { workspace } = useAuth()
  const { programs, loading, error, createProgram, setProgramStatus } = useTraining()
  const [open, setOpen] = useState(false)
  const [f, setF] = useState({ title: '', description: '', level: 'BEGINNER', delivery_mode: 'ONLINE', is_free: true, price: '' })
  const orgId = workspace?.organization?.id
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })

  async function submit(status: Program['status']) {
    if (!orgId) return
    const input: ProgramInput = {
      organization_id: orgId, title: f.title.trim(), description: f.description.trim(),
      level: f.level as Program['level'], delivery_mode: f.delivery_mode as Program['delivery_mode'],
      status, is_free: f.is_free, price: f.is_free ? 0 : Number(f.price) || 0,
    }
    try { await createProgram(input); setOpen(false); setF({ ...f, title: '', description: '', price: '' }) } catch { /* affiché en haut */ }
  }

  return (
    <>
      <PageHeader title="Programmes" action={<Button onClick={() => setOpen(!open)}>{open ? 'Fermer' : 'Nouveau programme'}</Button>} />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {open && (
          <Panel title="Nouveau programme">
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2"><Field label="Titre" required><Input value={f.title} onChange={set('title')} /></Field></div>
              <div className="sm:col-span-2"><Field label="Description"><Textarea rows={4} value={f.description} onChange={set('description')} /></Field></div>
              <Field label="Niveau"><Select value={f.level} onChange={set('level')}>{Object.entries(LEVEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
              <Field label="Mode"><Select value={f.delivery_mode} onChange={set('delivery_mode')}>{Object.entries(MODE).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
              <label className="flex items-center gap-2 text-[13.5px]"><input type="checkbox" checked={f.is_free} onChange={(e) => setF({ ...f, is_free: e.target.checked })} /> Gratuit</label>
              {!f.is_free && <Field label="Prix (TND)"><Input type="number" value={f.price} onChange={set('price')} /></Field>}
              <div className="flex gap-2 sm:col-span-2">
                <Button variant="discret" disabled={!f.title.trim()} onClick={() => void submit('DRAFT')}>Brouillon</Button>
                <Button disabled={!f.title.trim() || (!f.is_free && !(Number(f.price) > 0))} onClick={() => void submit('ACTIVE')}>Publier</Button>
              </div>
            </div>
          </Panel>
        )}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : programs.length === 0 ? (
            <EmptyState title="Aucun programme">Créez votre premier programme de formation.</EmptyState>
          ) : (
            <Table head={['Programme', 'Mode', 'Prix', 'Statut', '']}>
              {programs.map((p) => (
                <Row key={p.id}>
                  <Cell><span className="font-medium text-navy">{p.title}</span><p className="text-[12.5px] text-slate">{LEVEL[p.level]}</p></Cell>
                  <Cell className="text-[13px]">{MODE[p.delivery_mode]}</Cell>
                  <Cell className="text-[13px]">{price(p)}</Cell>
                  <Cell><Badge tone={p.status === 'ACTIVE' ? 'positif' : 'neutre'}>{PSTATUS[p.status]}</Badge></Cell>
                  <Cell className="text-right">
                    {p.status === 'DRAFT' && <Button size="sm" onClick={() => void setProgramStatus(p.id, 'ACTIVE').catch(() => {})}>Publier</Button>}
                    {p.status === 'ACTIVE' && <Button size="sm" variant="discret" onClick={() => void setProgramStatus(p.id, 'ARCHIVED').catch(() => {})}>Archiver</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
      </PageBody>
    </>
  )
}

export function FormationSessions() {
  const { programs, sessions, enrollments, loading, error, createSession, setSessionStatus } = useTraining()
  const [open, setOpen] = useState(false)
    const [selected, setSelected] = useState<string | null>(null)
  const [f, setF] = useState({ program_id: '', start_date: '', end_date: '', registration_deadline: '', capacity: '20', location_or_url: '' })
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const title = (id: string) => programs.find((p) => p.id === id)?.title ?? 'Programme'
  const ready = f.program_id && f.start_date && f.end_date && f.registration_deadline && f.location_or_url.trim()

  async function submit() {
    try {
      await createSession({
        program_id: f.program_id, capacity: Number(f.capacity) || 1, location_or_url: f.location_or_url.trim(),
        start_date: new Date(f.start_date).toISOString(), end_date: new Date(f.end_date).toISOString(),
        registration_deadline: new Date(f.registration_deadline).toISOString(),
      })
      setOpen(false)
    } catch { /* affiché en haut */ }
  }

  return (
    <>
      <PageHeader title="Sessions" action={<Button onClick={() => setOpen(!open)}>{open ? 'Fermer' : 'Planifier une session'}</Button>} />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {open && (
          <Panel title="Nouvelle session">
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Field label="Programme" required>
                  <Select value={f.program_id} onChange={set('program_id')}>
                    <option value="">Choisir…</option>
                    {programs.filter((p) => p.status === 'ACTIVE').map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                  </Select>
                </Field>
              </div>
              <Field label="Début" required><Input type="datetime-local" value={f.start_date} onChange={set('start_date')} /></Field>
              <Field label="Fin" required><Input type="datetime-local" value={f.end_date} onChange={set('end_date')} /></Field>
              <Field label="Clôture des inscriptions" required><Input type="datetime-local" value={f.registration_deadline} onChange={set('registration_deadline')} /></Field>
              <Field label="Capacité"><Input type="number" value={f.capacity} onChange={set('capacity')} /></Field>
              <div className="sm:col-span-2"><Field label="Lieu ou lien" required><Input value={f.location_or_url} onChange={set('location_or_url')} /></Field></div>
              <div className="sm:col-span-2"><Button disabled={!ready} onClick={() => void submit()}>Planifier</Button></div>
            </div>
          </Panel>
        )}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : sessions.length === 0 ? (
            <EmptyState title="Aucune session">Planifiez une session pour un programme actif.</EmptyState>
          ) : (
            <Table head={['Programme', 'Dates', 'Inscrits', 'Statut', '']}>
              {sessions.map((s) => (
                <Row key={s.id}>
                  <Cell><span className="font-medium text-navy">{title(s.program)}</span><p className="text-[12.5px] text-slate">{s.location_or_url}</p></Cell>
                  <Cell className="text-[13px]">{formatDate(s.start_date)} → {formatDate(s.end_date)}</Cell>
                  <Cell className="tnum text-[13px]">
                    <button className="font-medium text-teal hover:underline" onClick={() => setSelected(selected === s.id ? null : s.id)}>
                      {enrollments.filter((e) => e.session === s.id).length} / {s.capacity}
                    </button>
                  </Cell>                  <Cell><Badge tone={s.status === 'CANCELLED' ? 'negatif' : s.status === 'COMPLETED' ? 'neutre' : 'positif'}>{SSTATUS[s.status]}</Badge></Cell>
                  <Cell className="text-right">
                    {s.status === 'PLANNED' && (
                      <>
                        <Button size="sm" onClick={() => void setSessionStatus(s.id, 'ONGOING').catch(() => {})}>Démarrer</Button>{' '}
                        <Button size="sm" variant="discret" onClick={() => void setSessionStatus(s.id, 'CANCELLED').catch(() => {})}>Annuler</Button>
                      </>
                    )}
                    {s.status === 'ONGOING' && <Button size="sm" onClick={() => void setSessionStatus(s.id, 'COMPLETED').catch(() => {})}>Terminer</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>*        {selected && (
          <Panel title={`Inscrits — ${title(sessions.find((s) => s.id === selected)?.program ?? '')}`}>
            {enrollments.filter((e) => e.session === selected).length === 0 ? (
              <p className="px-5 py-4 text-[13.5px] text-slate">Aucune inscription pour cette session.</p>
            ) : (
              <ul className="divide-y divide-line/70">
                {enrollments.filter((e) => e.session === selected).map((e) => (
                  <li key={e.id} className="flex items-center justify-between gap-3 px-5 py-3">
                    <span className="text-[13.5px] text-navy">
                      Candidat {e.candidate_id.slice(0, 8)} · inscrit le {formatDate(e.enrolled_at)}
                    </span>
                    <span className="flex items-center gap-3">
                      {e.completion_rate !== null && <span className="tnum text-[12.5px] text-slate">{e.completion_rate} %</span>}
                      <Badge tone={e.status === 'COMPLETED' ? 'positif' : e.status === 'DROPPED' ? 'negatif' : 'neutre'}>{ENROLL[e.status]}</Badge>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        )}
      </PageBody>
    </>
  )
}