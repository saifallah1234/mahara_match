import { useState } from 'react'
import { PageBody, PageHeader } from './../components/layout'
import { Badge, Button, Cell, EmptyState, Field, Modal, Panel, Row, Select, StatTile, Table, Textarea, Input } from './../components/ui'
import { useStore } from '../state/store'
import { DELIVERY_LABEL, SKILL_LEVEL_LABEL, formatDate, formatPrice } from '../lib/format'
import type { DeliveryMode, SessionStatus, SkillLevel, TrainingProgram } from '../lib/types'

const SESSION_TONE: Record<SessionStatus, 'positif' | 'encours' | 'neutre' | 'negatif' | 'attention'> = {
  OUVERTE: 'positif',
  PLANIFIEE: 'encours',
  COMPLETE: 'attention',
  TERMINEE: 'neutre',
  ANNULEE: 'negatif',
}

const SESSION_TEXT: Record<SessionStatus, string> = {
  OUVERTE: 'Inscriptions ouvertes',
  PLANIFIEE: 'Planifiée',
  COMPLETE: 'Complète',
  TERMINEE: 'Terminée',
  ANNULEE: 'Annulée',
}

/* ------------------------------------------------------------------ */

export function FormationDashboard() {
  const { session, programs, sessions, enrollments, offers, skills } = useStore()
  if (!session) return null

  const mine = programs.filter((p) => p.organizationId === session.user.organizationId)
  const published = mine.filter((p) => p.status === 'PUBLISHED')
  const mySessions = sessions.filter((s) => mine.some((p) => p.id === s.programId))
  const myEnrollments = enrollments.filter((e) => mySessions.some((s) => s.id === e.sessionId))

  /* Demande du marché pour les compétences que l'organisme enseigne. */
  const taught = [...new Set(published.flatMap((p) => p.skillIds))]
  const demand = taught
    .map((skillId) => ({
      skillId,
      name: skills.find((s) => s.id === skillId)?.canonicalName ?? skillId,
      count: offers.filter((o) => o.status === 'PUBLISHED' && o.skills.some((os) => os.skillId === skillId)).length,
    }))
    .sort((a, b) => b.count - a.count)

  return (
    <>
      <PageHeader
        title="Espace formation"
      />

      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={published.length} label="Formations publiées" note={`${mine.length} au catalogue`} />
          <StatTile value={mySessions.filter((s) => s.status === 'OUVERTE').length} label="Sessions ouvertes" tone="teal" />
          <StatTile value={myEnrollments.length} label="Inscriptions" tone="leaf" />
          <StatTile value={taught.length} label="Compétences couvertes" />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="Demande du marché" description="Nombre d’offres ouvertes réclamant une compétence que vous enseignez.">
            {demand.length === 0 ? (
              <EmptyState title="Aucune formation publiée" />
            ) : (
              <ul className="divide-y divide-line/70">
                {demand.map((entry) => (
                  <li key={entry.skillId} className="flex items-center justify-between px-5 py-3 text-[13.5px]">
                    <span className="font-medium text-navy">{entry.name}</span>
                    <span className="tnum text-slate">
                      {entry.count} offre{entry.count > 1 ? 's' : ''}
                    </span>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Prochaines sessions">
            <ul className="divide-y divide-line/70">
              {mySessions
                .filter((s) => s.status === 'OUVERTE' || s.status === 'PLANIFIEE')
                .map((trainingSession) => {
                  const program = mine.find((p) => p.id === trainingSession.programId)
                  const count = enrollments.filter((e) => e.sessionId === trainingSession.id).length
                  return (
                    <li key={trainingSession.id} className="flex flex-wrap items-center justify-between gap-2 px-5 py-3">
                      <div className="min-w-0">
                        <p className="text-[13.5px] font-medium text-navy">{program?.title}</p>
                        <p className="text-[12.5px] text-slate">
                          Dès le {formatDate(trainingSession.startDate)} · {count} / {trainingSession.capacity} places
                        </p>
                      </div>
                      <Badge tone={SESSION_TONE[trainingSession.status]}>{SESSION_TEXT[trainingSession.status]}</Badge>
                    </li>
                  )
                })}
            </ul>
          </Panel>
        </div>

      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function FormationProgrammes() {
  const { session, programs, skills, publishProgram, organizationOf } = useStore()
  const [open, setOpen] = useState(false)
  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [prerequisites, setPrerequisites] = useState('')
  const [hours, setHours] = useState('')
  const [price, setPrice] = useState('')
  const [mode, setMode] = useState<DeliveryMode>('PRESENTIEL')
  const [level, setLevel] = useState<SkillLevel>('DEBUTANT')
  const [chosen, setChosen] = useState<string[]>([])

  if (!session) return null
  const mine = programs.filter((p) => p.organizationId === session.user.organizationId)

  const problems: string[] = []
  if (!title.trim()) problems.push('Le titre est obligatoire.')
  if (!description.trim()) problems.push('La description est obligatoire.')
  if (!hours) problems.push('La durée est obligatoire.')
  if (chosen.length === 0) problems.push('Au moins une compétence visée doit être sélectionnée.')

  function create(status: 'DRAFT' | 'PUBLISHED') {
    const program: TrainingProgram = {
      id: `tp-${Date.now().toString(36)}`,
      organizationId: session!.user.organizationId!,
      title: title.trim(),
      description: description.trim(),
      level,
      deliveryMode: mode,
      status,
      durationHours: Number(hours),
      priceTnd: price ? Number(price) : undefined,
      prerequisites: prerequisites.trim() || 'Aucun prérequis particulier.',
      contactEmail: session!.user.email,
      skillIds: chosen,
    }
    publishProgram(program)
    setOpen(false)
    setTitle('')
    setDescription('')
    setHours('')
    setPrice('')
    setChosen([])
  }

  return (
    <>
      <PageHeader
        title="Programmes de formation"
        action={<Button onClick={() => setOpen(true)}>Publier une formation</Button>}
      />

      <PageBody>
        <Panel>
          {mine.length === 0 ? (
            <EmptyState title="Aucun programme" action={<Button onClick={() => setOpen(true)}>Créer un programme</Button>} />
          ) : (
            <Table head={['Formation', 'Compétences visées', 'Modalité', 'Durée', 'Coût', 'Statut']}>
              {mine.map((program) => (
                <Row key={program.id}>
                  <Cell>
                    <p className="font-medium text-navy">{program.title}</p>
                    <p className="text-[12.5px] text-slate">{organizationOf(program.organizationId)?.legalName}</p>
                  </Cell>
                  <Cell>
                    <div className="flex flex-wrap gap-1.5">
                      {program.skillIds.map((id) => (
                        <Badge key={id} tone="teal">
                          {skills.find((s) => s.id === id)?.canonicalName}
                        </Badge>
                      ))}
                    </div>
                  </Cell>
                  <Cell className="text-[13px] text-slate">{DELIVERY_LABEL[program.deliveryMode]}</Cell>
                  <Cell className="tnum text-[13px] text-slate">{program.durationHours} h</Cell>
                  <Cell className="text-[13px] text-slate">{formatPrice(program.priceTnd)}</Cell>
                  <Cell>
                    <Badge
                      tone={program.status === 'PUBLISHED' ? 'positif' : program.status === 'DRAFT' ? 'neutre' : 'attention'}
                    >
                      {program.status === 'PUBLISHED' ? 'Publiée' : program.status === 'DRAFT' ? 'Brouillon' : 'Archivée'}
                    </Badge>
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
      </PageBody>

      <Modal
        open={open}
        onClose={() => setOpen(false)}
        title="Publier une formation"
        footer={
          <>
            <Button variant="secondaire" onClick={() => create('DRAFT')} disabled={!title.trim()}>
              Brouillon
            </Button>
            <Button onClick={() => create('PUBLISHED')} disabled={problems.length > 0}>
              Publier
            </Button>
          </>
        }
      >
        <div className="space-y-4">
          <Field label="Titre" required>
            <Input value={title} onChange={(e) => setTitle(e.target.value)} />
          </Field>
          <Field label="Objectifs et contenu" required>
            <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={4} />
          </Field>
          <Field label="Prérequis" hint="Ce que le candidat doit déjà savoir faire.">
            <Textarea value={prerequisites} onChange={(e) => setPrerequisites(e.target.value)} rows={2} />
          </Field>
          <div className="grid gap-4 sm:grid-cols-2">
            <Field label="Durée (heures)" required>
              <Input type="number" value={hours} onChange={(e) => setHours(e.target.value)} />
            </Field>
            <Field label="Coût (DT)" hint="Laisser vide affichera « non renseigné ».">
              <Input type="number" value={price} onChange={(e) => setPrice(e.target.value)} />
            </Field>
            <Field label="Modalité">
              <Select value={mode} onChange={(e) => setMode(e.target.value as DeliveryMode)}>
                {(Object.keys(DELIVERY_LABEL) as DeliveryMode[]).map((m) => (
                  <option key={m} value={m}>
                    {DELIVERY_LABEL[m]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Niveau">
              <Select value={level} onChange={(e) => setLevel(e.target.value as SkillLevel)}>
                {(Object.keys(SKILL_LEVEL_LABEL) as SkillLevel[]).map((l) => (
                  <option key={l} value={l}>
                    {SKILL_LEVEL_LABEL[l]}
                  </option>
                ))}
              </Select>
            </Field>
          </div>

          <Field label="Compétences visées" required hint="Choisies dans le référentiel commun, pour éviter les doublons ambigus.">
            <div className="max-h-44 space-y-1 overflow-y-auto rounded-[6px] border border-line p-2">
              {skills.map((skill) => (
                <label key={skill.id} className="flex items-center gap-2.5 rounded px-2 py-1 text-[13px] hover:bg-mist">
                  <input
                    type="checkbox"
                    checked={chosen.includes(skill.id)}
                    onChange={(e) =>
                      setChosen((list) => (e.target.checked ? [...list, skill.id] : list.filter((id) => id !== skill.id)))
                    }
                    className="accent-teal"
                  />
                  {skill.canonicalName}
                </label>
              ))}
            </div>
          </Field>

          {problems.length > 0 && (
            <ul className="space-y-1">
              {problems.map((p) => (
                <li key={p} className="text-[12.5px] text-coral">
                  {p}
                </li>
              ))}
            </ul>
          )}
        </div>
      </Modal>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function FormationSessions() {
  const { session, programs, sessions, enrollments, profileOf, userOf } = useStore()
  if (!session) return null

  const mine = programs.filter((p) => p.organizationId === session.user.organizationId)
  const mySessions = sessions
    .filter((s) => mine.some((p) => p.id === s.programId))
    .sort((a, b) => +new Date(a.startDate) - +new Date(b.startDate))

  return (
    <>
      <PageHeader
        title="Sessions et inscriptions"
        action={<Button>Planifier une session</Button>}
      />

      <PageBody className="space-y-5">
        {mySessions.map((trainingSession) => {
          const program = mine.find((p) => p.id === trainingSession.programId)
          const registered = enrollments.filter((e) => e.sessionId === trainingSession.id)
          return (
            <Panel
              key={trainingSession.id}
              title={program?.title}
              description={`Du ${formatDate(trainingSession.startDate)} au ${formatDate(trainingSession.endDate)} · ${trainingSession.locationOrUrl}`}
              action={<Badge tone={SESSION_TONE[trainingSession.status]}>{SESSION_TEXT[trainingSession.status]}</Badge>}
            >
              <div className="flex flex-wrap gap-6 border-b border-line px-5 py-3 text-[13px]">
                <span className="text-slate">
                  Inscrits <span className="tnum font-medium text-navy">{registered.length}</span> /{' '}
                  <span className="tnum">{trainingSession.capacity}</span>
                </span>
                <span className="text-slate">
                  Clôture des inscriptions{' '}
                  <span className="font-medium text-navy">{formatDate(trainingSession.registrationDeadline)}</span>
                </span>
              </div>

              {registered.length === 0 ? (
                <p className="px-5 py-4 text-[13px] text-slate">Aucune inscription enregistrée pour cette session.</p>
              ) : (
                <Table head={['Participant', 'Inscrit le', 'Progression', 'Statut']}>
                  {registered.map((enrollment) => {
                    const profile = profileOf(enrollment.candidateId)
                    const user = profile ? userOf(profile.userId) : undefined
                    return (
                      <Row key={enrollment.id}>
                        <Cell className="font-medium text-navy">
                          {user?.firstName} {user?.lastName}
                        </Cell>
                        <Cell className="text-[13px] text-slate">{formatDate(enrollment.enrolledAt)}</Cell>
                        <Cell className="tnum text-[13px] text-slate">{enrollment.completionRate} %</Cell>
                        <Cell>
                          <Badge tone={enrollment.status === 'TERMINE' ? 'positif' : 'encours'}>
                            {enrollment.status === 'INSCRIT'
                              ? 'Inscrit'
                              : enrollment.status === 'EN_COURS'
                                ? 'En cours'
                                : enrollment.status === 'TERMINE'
                                  ? 'Terminé'
                                  : 'Abandonné'}
                          </Badge>
                        </Cell>
                      </Row>
                    )
                  })}
                </Table>
              )}
            </Panel>
          )
        })}

      </PageBody>
    </>
  )
}
