import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../components/layout'
import { Badge, Button, Cell, ConfirmDialog, EmptyState, Field, Input, Meter, Panel, Row, Select, StatTile, Table, Textarea } from '../components/ui'
import { useAuth } from '../state/auth'
import { useTraining } from '../state/training'
import { MembersPanel } from '../components/members'
import { ENROLLMENT_STATUS_LABEL, PROGRAM_STATUS_LABEL, SESSION_STATUS_LABEL, formatDate, formatDateTime, formatPrice, labelFor, skillLabel, toDateTimeInput } from '../lib/format'
import type { Enrollment, Program, ProgramSkill, Session } from '../api/training'

const MODE = { ONLINE: 'En ligne', PRESENTIAL: 'Présentiel', HYBRID: 'Hybride' } as const
const LEVEL = { BEGINNER: 'Débutant', INTERMEDIATE: 'Intermédiaire', ADVANCED: 'Avancé' } as const
const TARGET_LEVEL = { BEGINNER: 'Débutant', INTERMEDIATE: 'Intermédiaire', ADVANCED: 'Avancé', EXPERT: 'Expert' } as const
const blankProgram = { title: '', description: '', level: 'BEGINNER', delivery_mode: 'ONLINE', is_free: true, price: '' }
const blankSession = { program_id: '', start_date: '', end_date: '', registration_deadline: '', capacity: '20', location_or_url: '' }

/** Une inscription abandonnée libère sa place, comme dans la règle de capacité du backend. */
const seatsTaken = (enrollments: Enrollment[], sessionId: string) =>
  enrollments.filter((e) => e.session === sessionId && e.status !== 'DROPPED').length
const byStart = (a: Session, b: Session) => new Date(a.start_date).getTime() - new Date(b.start_date).getTime()

export function FormationDashboard() {
  const { workspace } = useAuth()
  const { programs, sessions, enrollments, loading, error } = useTraining()
  const title = (id: string) => programs.find((p) => p.id === id)?.title ?? 'Programme'
  const upcoming = sessions.filter((s) => s.status === 'PLANNED' || s.status === 'ONGOING').sort(byStart).slice(0, 5)
  const recent = [...enrollments].sort((a, b) => new Date(b.enrolled_at).getTime() - new Date(a.enrolled_at).getTime()).slice(0, 5)
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
        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Prochaines sessions" action={<Link to="/formation/sessions" className="text-[13px] font-medium text-teal">Toutes les sessions</Link>}>
            {upcoming.length === 0 ? <EmptyState title="Aucune session à venir" /> : (
              <ul className="divide-y divide-line/70">
                {upcoming.map((s) => {
                  const taken = seatsTaken(enrollments, s.id)
                  return (
                    <li key={s.id}>
                      <Link to="/formation/sessions" className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-mist">
                        <span className="min-w-0">
                          <span className="block truncate text-[13.5px] font-medium text-navy">{title(s.program)}</span>
                          <span className="text-[12.5px] text-slate">{formatDateTime(s.start_date)}</span>
                        </span>
                        <span className="w-40 shrink-0"><Meter value={Math.round((taken / s.capacity) * 100)} label={`${taken} / ${s.capacity} inscrits`} /></span>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </Panel>
          <Panel title="Inscriptions récentes" action={<Link to="/formation/sessions" className="text-[13px] font-medium text-teal">Voir les sessions</Link>}>
            {recent.length === 0 ? <EmptyState title="Aucune inscription" /> : (
              <ul className="divide-y divide-line/70">
                {recent.map((e) => (
                  <li key={e.id}>
                    <Link to="/formation/sessions" className="flex items-center justify-between gap-4 px-5 py-3 hover:bg-mist">
                      <span className="min-w-0">
                        <span className="block truncate text-[13.5px] font-medium text-navy">{e.applicant.first_name} {e.applicant.last_name}</span>
                        <span className="block truncate text-[12.5px] text-slate">{e.program_title}</span>
                      </span>
                      <span className="shrink-0 text-[12.5px] text-slate">inscrit le {formatDate(e.enrolled_at)}</span>
                    </Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        </div>
      </PageBody>
    </>
  )
}

export function FormationOrganisme() {
  const { workspace } = useAuth()
  const org = workspace?.organization
  if (!org) return <PageBody><Panel className="p-8"><p className="text-center text-[14px] text-slate">Aucune organisation rattachée à ce compte.</p></Panel></PageBody>
  return (
    <>
      <PageHeader title="Mon organisme" />
      <PageBody className="space-y-6">
        <Panel title="Organisme">
          <dl className="grid gap-4 px-5 py-4 text-[13.5px] sm:grid-cols-2">
            <div><dt className="text-slate">Raison sociale</dt><dd className="font-medium text-navy">{org.legal_name}</dd></div>
            <div><dt className="text-slate">Statut de vérification</dt><dd className="text-navy">{org.verification_status === 'VERIFIED' ? 'Vérifié' : 'En attente'}</dd></div>
          </dl>
        </Panel>
        <MembersPanel organizationId={org.id} />
      </PageBody>
    </>
  )
}

export function FormationProgrammes() {
  const { workspace } = useAuth()
  const { programs, skills, skillCatalogue, loading, error, createProgram, updateProgram, addSkill, removeSkill, setProgramStatus } = useTraining()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Program | null>(null)
  const [f, setF] = useState(blankProgram)
  const [chosen, setChosen] = useState<{ skillId: string; level: ProgramSkill['target_level'] }[]>([])
  const [pick, setPick] = useState<{ skillId: string; level: ProgramSkill['target_level'] }>({ skillId: '', level: 'BEGINNER' })
  const orgId = workspace?.organization?.id
  const [archiving, setArchiving] = useState<Program | null>(null)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const skillName = (id: string) => skillLabel(skillCatalogue.find((s) => s.id === id)?.canonical_name ?? id)
  const skillsOf = (programId: string) => skills.filter((s) => s.program === programId)

  function close() {
    setOpen(false); setEditing(null); setF(blankProgram); setChosen([])
  }

  function edit(p: Program) {
    setEditing(p); setOpen(true)
    setF({ title: p.title, description: p.description, level: p.level, delivery_mode: p.delivery_mode, is_free: p.is_free, price: p.is_free ? '' : p.price })
  }

  async function submit(publish: boolean) {
    if (!orgId) return
    const fields = {
      title: f.title.trim(), description: f.description.trim(),
      level: f.level as Program['level'], delivery_mode: f.delivery_mode as Program['delivery_mode'],
      is_free: f.is_free, price: f.is_free ? 0 : Number(f.price) || 0,
    }
    try {
      if (editing) {
        await updateProgram(editing.id, fields)
      } else {
        const id = await createProgram({ ...fields, organization_id: orgId, status: 'DRAFT' }, chosen)
        if (publish) await setProgramStatus(id, 'ACTIVE')
      }
      close()
    } catch { /* affiché en haut */ }
  }

  return (
    <>
      <PageHeader title="Programmes" action={<Button onClick={() => (open ? close() : setOpen(true))}>{open ? 'Fermer' : 'Nouveau programme'}</Button>} />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {open && (
          <Panel title={editing ? `Modifier « ${editing.title} »` : 'Nouveau programme'}>
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2"><Field label="Titre" required><Input value={f.title} onChange={set('title')} /></Field></div>
              <div className="sm:col-span-2"><Field label="Description"><Textarea rows={4} value={f.description} onChange={set('description')} /></Field></div>
              <Field label="Niveau"><Select value={f.level} onChange={set('level')}>{Object.entries(LEVEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
              <Field label="Mode"><Select value={f.delivery_mode} onChange={set('delivery_mode')}>{Object.entries(MODE).map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select></Field>
              <label className="flex items-center gap-2 text-[13.5px]"><input type="checkbox" checked={f.is_free} onChange={(e) => setF({ ...f, is_free: e.target.checked })} /> Gratuit</label>
              {!f.is_free && <Field label="Prix (TND)"><Input type="number" value={f.price} onChange={set('price')} /></Field>}
              {!editing && (
                <div className="space-y-3 sm:col-span-2">
                  <p className="text-[13.5px] font-medium text-navy">Compétences du programme</p>
                  <div className="flex flex-wrap gap-2">
                    <Select value={pick.skillId} onChange={(e) => setPick({ ...pick, skillId: e.target.value })}>
                      <option value="">Choisir une compétence…</option>
                      {skillCatalogue.map((s) => <option key={s.id} value={s.id}>{skillLabel(s.canonical_name)}</option>)}
                    </Select>
                    <Select value={pick.level} onChange={(e) => setPick({ ...pick, level: e.target.value as ProgramSkill['target_level'] })}>
                      {Object.entries(TARGET_LEVEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                    </Select>
                    <Button variant="discret" disabled={!pick.skillId || chosen.some((c) => c.skillId === pick.skillId)} onClick={() => { setChosen([...chosen, pick]); setPick({ ...pick, skillId: '' }) }}>Ajouter</Button>
                  </div>
                  {chosen.map((c) => (
                    <div key={c.skillId} className="flex items-center justify-between gap-3 text-[13.5px]">
                      <span>{skillName(c.skillId)} · {TARGET_LEVEL[c.level]}</span>
                      <Button size="sm" variant="discret" onClick={() => setChosen(chosen.filter((x) => x.skillId !== c.skillId))}>Retirer</Button>
                    </div>
                  ))}
                </div>
              )}
              <div className="flex flex-wrap items-center gap-3 sm:col-span-2">
                {editing ? (
                  <Button disabled={!f.title.trim() || (!f.is_free && !(Number(f.price) > 0))} onClick={() => void submit(false)}>Enregistrer</Button>
                ) : (
                  <>
                    <Button variant="discret" disabled={!f.title.trim()} onClick={() => void submit(false)}>Brouillon</Button>
                    <Button disabled={!f.title.trim() || chosen.length === 0 || (!f.is_free && !(Number(f.price) > 0))} onClick={() => void submit(true)}>Publier</Button>
                    {chosen.length === 0 && <p className="text-[12.5px] text-slate">Ajoutez au moins une compétence avant de publier.</p>}
                  </>
                )}
              </div>
            </div>
          </Panel>
        )}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : programs.length === 0 ? (
            <EmptyState title="Aucun programme">Créez votre premier programme de formation.</EmptyState>
          ) : (
            <Table head={['Programme', 'Mode', 'Prix', 'Statut', '']}>
              {programs.map((p) => {
                const own = skillsOf(p.id)
                return (
                  <Row key={p.id}>
                    <Cell>
                      <span className="font-medium text-navy">{p.title}</span>
                      <p className="text-[12.5px] text-slate">{LEVEL[p.level]}</p>
                      <ul className="mt-2 space-y-1">
                        {own.map((s) => (
                          <li key={s.id} className="flex items-center gap-2 text-[12.5px]">
                            <span>{skillName(s.skill_id)} · {TARGET_LEVEL[s.target_level]}</span>
                            {p.status !== 'ARCHIVED' && <Button size="sm" variant="discret" onClick={() => void removeSkill(s.id).catch(() => {})}>Retirer</Button>}
                          </li>
                        ))}
                      </ul>
                      {p.status !== 'ARCHIVED' && (
                        <Select className="mt-2 text-[12.5px]" value="" onChange={(e) => { if (e.target.value) void addSkill(p.id, e.target.value, 'BEGINNER').catch(() => {}) }}>
                          <option value="">Ajouter une compétence…</option>
                          {skillCatalogue.filter((s) => !own.some((o) => o.skill_id === s.id)).map((s) => <option key={s.id} value={s.id}>{skillLabel(s.canonical_name)}</option>)}
                        </Select>
                      )}
                    </Cell>
                    <Cell className="text-[13px]">{MODE[p.delivery_mode]}</Cell>
                    <Cell className="text-[13px]">{formatPrice(p.price)}</Cell>
                    <Cell><Badge tone={p.status === 'ACTIVE' ? 'positif' : 'neutre'}>{labelFor(PROGRAM_STATUS_LABEL, p.status)}</Badge></Cell>
                    <Cell className="text-right">
                      <Button size="sm" variant="discret" onClick={() => edit(p)}>Modifier</Button>{' '}
                      {p.status === 'DRAFT' && (
                        <>
                          <Button size="sm" disabled={own.length === 0} onClick={() => void setProgramStatus(p.id, 'ACTIVE').catch(() => {})}>Publier</Button>
                          {own.length === 0 && <p className="mt-1 text-[12px] text-slate">Ajoutez une compétence avant de publier.</p>}
                        </>
                      )}
                      {p.status === 'ACTIVE' && <Button size="sm" variant="discret" onClick={() => setArchiving(p)}>Archiver</Button>}
                      {p.status === 'ARCHIVED' && <Button size="sm" variant="discret" onClick={() => void setProgramStatus(p.id, 'DRAFT').catch(() => {})}>Remettre en brouillon</Button>}
                    </Cell>
                  </Row>
                )
              })}
            </Table>
          )}
        </Panel>
        {archiving && (
          <ConfirmDialog
            title="Archiver ce programme ?"
            danger
            onCancel={() => setArchiving(null)}
            onConfirm={() => { void setProgramStatus(archiving.id, 'ARCHIVED').catch(() => {}); setArchiving(null) }}
          >
            Le programme « {archiving.title} » sera archivé et ne sera plus proposé au catalogue.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}

/** Progression d'un inscrit (0 à 100), enregistrée à la sortie du champ. Le backend refuse les valeurs hors règle. */
function ProgressInput({ enrollment, disabled, onSave }: { enrollment: Enrollment; disabled: boolean; onSave: (rate: number) => Promise<void> }) {
  const saved = Number(enrollment.completion_rate ?? 0)
  const [value, setValue] = useState(String(saved))
  const locked = disabled || enrollment.status === 'COMPLETED' || enrollment.status === 'DROPPED'
  return (
    <span className="flex items-center gap-1.5">
      <Input
        aria-label="Progression"
        type="number"
        min={0}
        max={100}
        value={value}
        disabled={locked}
        className="w-20 py-1 text-[12.5px]"
        onChange={(e) => setValue(e.target.value)}
        onBlur={() => {
          const rate = Number(value)
          if (value === '' || rate === saved) { setValue(String(saved)); return }
          void onSave(rate).catch(() => setValue(String(saved)))
        }}
      />
      <span className="text-[12.5px] text-slate">%</span>
    </span>
  )
}

export function FormationSessions() {
  const { programs, sessions, enrollments, loading, error, createSession, updateSession, setSessionStatus, setProgress } = useTraining()
  const [open, setOpen] = useState(false)
  const [editing, setEditing] = useState<Session | null>(null)
  const [selected, setSelected] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState<(typeof sessions)[number] | null>(null)
  const [f, setF] = useState(blankSession)
  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const title = (id: string) => programs.find((p) => p.id === id)?.title ?? 'Programme'
  const picked = sessions.find((s) => s.id === selected)
  const ready = f.program_id && f.start_date && f.end_date && f.registration_deadline && f.location_or_url.trim()

  function close() {
    setOpen(false); setEditing(null); setF(blankSession)
  }

  function edit(s: Session) {
    setEditing(s); setOpen(true)
    setF({
      program_id: s.program, start_date: toDateTimeInput(s.start_date), end_date: toDateTimeInput(s.end_date),
      registration_deadline: toDateTimeInput(s.registration_deadline), capacity: String(s.capacity), location_or_url: s.location_or_url,
    })
  }

  async function submit() {
    try {
      const fields = {
        capacity: Number(f.capacity) || 1, location_or_url: f.location_or_url.trim(),
        start_date: new Date(f.start_date).toISOString(), end_date: new Date(f.end_date).toISOString(),
        registration_deadline: new Date(f.registration_deadline).toISOString(),
      }
      if (editing) await updateSession(editing.id, fields)
      else await createSession({ program_id: f.program_id, ...fields })
      close()
    } catch { /* affiché en haut */ }
  }

  return (
    <>
      <PageHeader title="Sessions" action={<Button onClick={() => (open ? close() : setOpen(true))}>{open ? 'Fermer' : 'Planifier une session'}</Button>} />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {open && (
          <Panel title={editing ? 'Modifier la session' : 'Nouvelle session'}>
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <div className="sm:col-span-2">
                <Field label="Programme" required>
                  <Select value={f.program_id} disabled={editing !== null} onChange={set('program_id')}>
                    <option value="">Choisir…</option>
                    {programs.filter((p) => p.status === 'ACTIVE' || p.id === f.program_id).map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
                  </Select>
                </Field>
              </div>
              <Field label="Début" required><Input type="datetime-local" value={f.start_date} onChange={set('start_date')} /></Field>
              <Field label="Fin" required><Input type="datetime-local" value={f.end_date} onChange={set('end_date')} /></Field>
              <Field label="Clôture des inscriptions" required><Input type="datetime-local" value={f.registration_deadline} onChange={set('registration_deadline')} /></Field>
              <Field label="Capacité"><Input type="number" value={f.capacity} onChange={set('capacity')} /></Field>
              <div className="sm:col-span-2"><Field label="Lieu ou lien" required><Input value={f.location_or_url} onChange={set('location_or_url')} /></Field></div>
              <div className="sm:col-span-2"><Button disabled={!ready} onClick={() => void submit()}>{editing ? 'Enregistrer' : 'Planifier'}</Button></div>
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
                  <Cell className="text-[13px]">{formatDateTime(s.start_date)} → {formatDateTime(s.end_date)}</Cell>
                  <Cell className="tnum text-[13px]">
                    <Button size="sm" variant="discret" className="font-medium text-teal" onClick={() => setSelected(selected === s.id ? null : s.id)}>
                      {seatsTaken(enrollments, s.id)} / {s.capacity}
                    </Button>
                  </Cell>
                  <Cell><Badge tone={s.status === 'CANCELLED' ? 'negatif' : s.status === 'COMPLETED' ? 'neutre' : 'positif'}>{labelFor(SESSION_STATUS_LABEL, s.status)}</Badge></Cell>
                  <Cell className="text-right">
                    {(s.status === 'PLANNED' || s.status === 'ONGOING') && <Button size="sm" variant="discret" onClick={() => edit(s)}>Modifier</Button>}{' '}
                    {s.status === 'PLANNED' && (
                      <>
                        <Button size="sm" onClick={() => void setSessionStatus(s.id, 'ONGOING').catch(() => {})}>Démarrer</Button>{' '}
                        <Button size="sm" variant="discret" onClick={() => setCancelling(s)}>Annuler</Button>
                      </>
                    )}
                    {s.status === 'ONGOING' && <Button size="sm" onClick={() => void setSessionStatus(s.id, 'COMPLETED').catch(() => {})}>Terminer</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
        {picked && (
          <Panel title={`Inscrits — ${title(picked.program)}`}>
            {enrollments.filter((e) => e.session === picked.id).length === 0 ? (
              <EmptyState title="Aucune inscription pour cette session." />
            ) : (
              <ul className="divide-y divide-line/70">
                {enrollments.filter((e) => e.session === picked.id).map((e) => (
                  <li key={e.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                    <span className="text-[13.5px] text-navy">
                      {e.applicant.first_name} {e.applicant.last_name} · {e.applicant.email} · inscrit le {formatDate(e.enrolled_at)}
                    </span>
                    <span className="flex items-center gap-3">
                      <ProgressInput
                        key={`${e.id}-${e.completion_rate}`}
                        enrollment={e}
                        disabled={picked.status === 'CANCELLED'}
                        onSave={(rate) => setProgress(e.id, rate)}
                      />
                      <Badge tone={e.status === 'COMPLETED' ? 'positif' : e.status === 'DROPPED' ? 'negatif' : 'neutre'}>{labelFor(ENROLLMENT_STATUS_LABEL, e.status)}</Badge>
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>
        )}
        {cancelling && (
          <ConfirmDialog
            title="Annuler cette session ?"
            danger
            onCancel={() => setCancelling(null)}
            onConfirm={() => { void setSessionStatus(cancelling.id, 'CANCELLED').catch(() => {}); setCancelling(null) }}
          >
            La session du {formatDate(cancelling.start_date)} au {formatDate(cancelling.end_date)} sera annulée.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}
