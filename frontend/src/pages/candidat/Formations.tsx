import { useMemo, useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Field, Panel, Select, Tabs } from '../../components/ui'
import { useStore } from '../../state/store'
import { skillGaps } from '../../lib/matching'
import { DELIVERY_LABEL, SKILL_LEVEL_LABEL, formatDate, formatPrice } from '../../lib/format'
import type { DeliveryMode } from '../../lib/types'

type Tab = 'recommandees' | 'catalogue' | 'mes-formations'

export default function CandidatFormations() {
  const { currentProfile, programs, sessions, enrollments, offers, skills, organizationOf, enroll } = useStore()
  const [tab, setTab] = useState<Tab>('recommandees')
  const [mode, setMode] = useState('')

  const gaps = useMemo(
    () => (currentProfile ? skillGaps(currentProfile, offers, skills) : []),
    [currentProfile, offers, skills],
  )

  if (!currentProfile) return null

  const published = programs.filter((p) => p.status === 'PUBLISHED')
  const gapIds = gaps.map((g) => g.skillId)

  /** Une formation n'est recommandée que si elle répond à un écart identifiable. */
  const recommended = published
    .map((program) => ({
      program,
      reasons: program.skillIds.filter((id) => gapIds.includes(id)),
    }))
    .filter((r) => r.reasons.length > 0)
    .sort((a, b) => b.reasons.length - a.reasons.length)

  const catalogue = published.filter((p) => !mode || p.deliveryMode === mode)
  const mine = enrollments.filter((e) => e.candidateId === currentProfile.id)

  function sessionsOf(programId: string) {
    return sessions.filter((s) => s.programId === programId && (s.status === 'OUVERTE' || s.status === 'PLANIFIEE'))
  }

  return (
    <>
      <PageHeader
        title="Formations"
      />

      <PageBody className="space-y-5">
        <Tabs<Tab>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'recommandees', label: 'Recommandées', count: recommended.length },
            { id: 'catalogue', label: 'Catalogue', count: published.length },
            { id: 'mes-formations', label: 'Mes inscriptions', count: mine.length },
          ]}
        />

        {tab === 'recommandees' && (
          <>
            {recommended.length === 0 ? (
              <Panel>
                <EmptyState title="Aucune formation recommandée pour l’instant">
                  Vos compétences confirmées couvrent les offres ouvertes consultées. Les recommandations apparaissent
                  dès qu’un écart est repéré.
                </EmptyState>
              </Panel>
            ) : (
              <div className="space-y-4">
                {recommended.map(({ program, reasons }) => {
                  const open = sessionsOf(program.id)
                  return (
                    <Panel key={program.id}>
                      <div className="border-b border-line px-5 py-4">
                        <div className="flex flex-wrap items-start justify-between gap-3">
                          <div className="min-w-0">
                            <h2 className="text-[15px] font-semibold text-navy">{program.title}</h2>
                            <p className="mt-0.5 text-[13px] text-slate">
                              {organizationOf(program.organizationId)?.legalName} ·{' '}
                              {DELIVERY_LABEL[program.deliveryMode]} · {program.durationHours} h ·{' '}
                              {SKILL_LEVEL_LABEL[program.level]}
                            </p>
                          </div>
                          <p className="shrink-0 text-[14px] font-medium text-navy">{formatPrice(program.priceTnd)}</p>
                        </div>

                        <div className="mt-3 rounded-[6px] border-l-[3px] border-l-teal bg-mist/60 px-4 py-2.5">
                          <p className="text-[13px] text-navy">
                            <span className="font-medium">Pourquoi cette formation </span>— elle enseigne{' '}
                            {reasons
                              .map((id) => skills.find((s) => s.id === id)?.canonicalName)
                              .filter(Boolean)
                              .join(', ')}
                            , compétence{reasons.length > 1 ? 's' : ''} demandée{reasons.length > 1 ? 's' : ''} par des
                            offres ouvertes et absente{reasons.length > 1 ? 's' : ''} de votre profil.
                          </p>
                        </div>
                      </div>

                      <div className="px-5 py-4">
                        <p className="text-[13.5px] leading-relaxed text-navy">{program.description}</p>
                        <p className="mt-2 text-[13px] text-slate">
                          <span className="font-medium text-navy">Prérequis </span>
                          {program.prerequisites}
                        </p>
                      </div>

                      {open.length === 0 ? (
                        <p className="border-t border-line px-5 py-3.5 text-[13px] text-slate">
                          Aucune session ouverte à l’inscription. Contact : {program.contactEmail}
                        </p>
                      ) : (
                        <ul className="divide-y divide-line/70 border-t border-line">
                          {open.map((trainingSession) => {
                            const already = mine.some((e) => e.sessionId === trainingSession.id)
                            return (
                              <li
                                key={trainingSession.id}
                                className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5"
                              >
                                <div>
                                  <p className="text-[13.5px] text-navy">
                                    Du {formatDate(trainingSession.startDate)} au {formatDate(trainingSession.endDate)}
                                  </p>
                                  <p className="text-[12.5px] text-slate">
                                    {trainingSession.locationOrUrl} · inscriptions jusqu’au{' '}
                                    {formatDate(trainingSession.registrationDeadline)}
                                  </p>
                                </div>
                                {already ? (
                                  <Badge tone="positif">Inscrite</Badge>
                                ) : (
                                  <Button size="sm" variant="secondaire" onClick={() => enroll(trainingSession.id)}>
                                    S’inscrire
                                  </Button>
                                )}
                              </li>
                            )
                          })}
                        </ul>
                      )}
                    </Panel>
                  )
                })}
              </div>
            )}

          </>
        )}

        {tab === 'catalogue' && (
          <>
            <Panel>
              <div className="grid gap-4 p-5 sm:grid-cols-3">
                <Field label="Modalité">
                  <Select value={mode} onChange={(e) => setMode(e.target.value)}>
                    <option value="">Toutes</option>
                    {(Object.keys(DELIVERY_LABEL) as DeliveryMode[]).map((m) => (
                      <option key={m} value={m}>
                        {DELIVERY_LABEL[m]}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
            </Panel>

            <div className="grid gap-3 lg:grid-cols-2">
              {catalogue.map((program) => (
                <article key={program.id} className="rounded-[10px] border border-line bg-white p-4 shadow-panel">
                  <h2 className="text-[15px] font-semibold text-navy">{program.title}</h2>
                  <p className="mt-0.5 text-[13px] text-slate">{organizationOf(program.organizationId)?.legalName}</p>
                  <p className="mt-2 text-[13px] leading-relaxed text-navy">{program.description}</p>
                  <div className="mt-3 flex flex-wrap gap-1.5">
                    {program.skillIds.map((id) => (
                      <Badge key={id} tone="teal">
                        {skills.find((s) => s.id === id)?.canonicalName}
                      </Badge>
                    ))}
                  </div>
                  <dl className="mt-3 grid grid-cols-2 gap-x-4 gap-y-1 text-[12.5px]">
                    <div className="flex justify-between">
                      <dt className="text-slate">Modalité</dt>
                      <dd className="text-navy">{DELIVERY_LABEL[program.deliveryMode]}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate">Durée</dt>
                      <dd className="text-navy">{program.durationHours} h</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate">Niveau</dt>
                      <dd className="text-navy">{SKILL_LEVEL_LABEL[program.level]}</dd>
                    </div>
                    <div className="flex justify-between">
                      <dt className="text-slate">Coût</dt>
                      <dd className="text-navy">{formatPrice(program.priceTnd)}</dd>
                    </div>
                  </dl>
                </article>
              ))}
            </div>
          </>
        )}

        {tab === 'mes-formations' && (
          <Panel title="Mes inscriptions">
            {mine.length === 0 ? (
              <EmptyState title="Aucune inscription">
                Les formations recommandées correspondent aux compétences qui vous manquent sur les offres ouvertes.
              </EmptyState>
            ) : (
              <ul className="divide-y divide-line/70">
                {mine.map((enrollment) => {
                  const trainingSession = sessions.find((s) => s.id === enrollment.sessionId)
                  const program = programs.find((p) => p.id === trainingSession?.programId)
                  if (!program || !trainingSession) return null
                  return (
                    <li key={enrollment.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4">
                      <div className="min-w-0">
                        <p className="text-[14px] font-medium text-navy">{program.title}</p>
                        <p className="mt-0.5 text-[12.5px] text-slate">
                          {organizationOf(program.organizationId)?.legalName} · du{' '}
                          {formatDate(trainingSession.startDate)} au {formatDate(trainingSession.endDate)}
                        </p>
                      </div>
                      <Badge tone={enrollment.status === 'TERMINE' ? 'positif' : 'encours'}>
                        {enrollment.status === 'INSCRIT'
                          ? 'Inscrite'
                          : enrollment.status === 'EN_COURS'
                            ? `En cours — ${enrollment.completionRate} %`
                            : enrollment.status === 'TERMINE'
                              ? 'Terminée'
                              : 'Abandonnée'}
                      </Badge>
                    </li>
                  )
                })}
              </ul>
            )}
          </Panel>
        )}
      </PageBody>
    </>
  )
}
