import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Field, Modal, Panel, Select, Textarea } from '../../components/ui'
import { MatchLedger, ScoreDial, StatusPill, StatusTimeline } from '../../components/domain'
import { useStore } from '../../state/store'
import { computeMatch } from '../../lib/matching'
import { APPLICATION_FLOW, STATUS_LABEL, TRANSITION_LABEL, allowedTransitions } from '../../lib/statusMachine'
import { cx, formatDate, formatPlace, relativeDays } from '../../lib/format'
import type { ApplicationStatus } from '../../lib/types'

/** Colonnes du pipeline : le cycle nominal, plus la sortie « Refusée ». */
const COLUMNS: ApplicationStatus[] = [...APPLICATION_FLOW, 'REJECTED']

export default function RecruteurCandidatures() {
  const { session, offers, applications, profileOf, userOf, skills, transition, cvOf } = useStore()
  const [selected, setSelected] = useState<string | null>(null)
  const [pending, setPending] = useState<{ id: string; next: ApplicationStatus } | null>(null)
  const [reason, setReason] = useState('')
  const [offerFilter, setOfferFilter] = useState('')

  if (!session) return null

  const myOffers = offers.filter((o) => o.createdBy === session.user.id)
  const received = applications.filter(
    (a) => myOffers.some((o) => o.id === a.offerId) && (!offerFilter || a.offerId === offerFilter),
  )

  const detail = selected ? received.find((a) => a.id === selected) : null
  const detailOffer = detail ? offers.find((o) => o.id === detail.offerId) : null
  const detailProfile = detail ? profileOf(detail.candidateId) : null
  const detailUser = detailProfile ? userOf(detailProfile.userId) : null

  function runTransition() {
    if (!pending) return
    transition(pending.id, pending.next, reason || undefined)
    setPending(null)
    setReason('')
  }

  return (
    <>
      <PageHeader
        title="Candidatures reçues"
        action={
          <Select value={offerFilter} onChange={(e) => setOfferFilter(e.target.value)} className="min-w-56">
            <option value="">Toutes mes offres</option>
            {myOffers.map((offer) => (
              <option key={offer.id} value={offer.id}>
                {offer.title}
              </option>
            ))}
          </Select>
        }
      />

      <PageBody className="space-y-5">
        {received.length === 0 ? (
          <Panel>
            <EmptyState title="Aucune candidature reçue">
              Les dossiers déposés sur vos offres apparaîtront ici, classés par étape du cycle.
            </EmptyState>
          </Panel>
        ) : (
          <div className="overflow-x-auto pb-2">
            <div className="flex min-w-max gap-3">
              {COLUMNS.map((status) => {
                const column = received.filter((a) => a.status === status)
                return (
                  <section key={status} className="w-64 shrink-0">
                    <header className="mb-2 flex items-center justify-between px-1">
                      <h2 className="text-[13px] font-semibold text-navy">{STATUS_LABEL[status]}</h2>
                      <span className="tnum text-[12px] text-slate">{column.length}</span>
                    </header>
                    <div
                      className={cx(
                        'min-h-24 space-y-2 rounded-[8px] p-2',
                        status === 'REJECTED' ? 'bg-coral/5' : status === 'HIRED' ? 'bg-leaf/6' : 'bg-mist/50',
                      )}
                    >
                      {column.map((application) => {
                        const profile = profileOf(application.candidateId)
                        const offer = offers.find((o) => o.id === application.offerId)
                        const user = profile ? userOf(profile.userId) : undefined
                        if (!profile || !offer) return null
                        const match = computeMatch(profile, offer, skills)
                        return (
                          <button
                            key={application.id}
                            onClick={() => setSelected(application.id)}
                            className="w-full rounded-[8px] border border-line bg-white p-3 text-left shadow-panel transition-colors hover:border-teal"
                          >
                            <div className="flex items-start gap-3">
                              <ScoreDial score={match.score} available={match.available} size={38} />
                              <div className="min-w-0 flex-1">
                                <p className="truncate text-[13.5px] font-medium text-navy">
                                  {user?.firstName} {user?.lastName}
                                </p>
                                <p className="truncate text-[12px] text-slate">{offer.title}</p>
                                <p className="mt-1 text-[11.5px] text-slate">{relativeDays(application.appliedAt)}</p>
                              </div>
                            </div>
                            {match.mandatoryMissingCount > 0 && (
                              <p className="mt-2 text-[11.5px] text-coral">
                                {match.mandatoryMissingCount} obligatoire
                                {match.mandatoryMissingCount > 1 ? 's' : ''} manquante
                                {match.mandatoryMissingCount > 1 ? 's' : ''}
                              </p>
                            )}
                          </button>
                        )
                      })}
                      {column.length === 0 && <p className="px-2 py-3 text-[12px] text-slate/70">—</p>}
                    </div>
                  </section>
                )
              })}
            </div>
          </div>
        )}

      </PageBody>

      {/* Dossier détaillé */}
      <Modal
        open={detail !== null}
        onClose={() => setSelected(null)}
        title={detailUser ? `${detailUser.firstName} ${detailUser.lastName}` : 'Dossier'}
        footer={
          detail && (
            <div className="flex w-full flex-wrap items-center justify-between gap-2">
              <StatusPill status={detail.status} />
              <div className="flex flex-wrap gap-2">
                {allowedTransitions(detail.status, 'RECRUITER').map((next) => (
                  <Button
                    key={next}
                    size="sm"
                    variant={next === 'REJECTED' ? 'danger' : 'primaire'}
                    onClick={() => setPending({ id: detail.id, next })}
                  >
                    {TRANSITION_LABEL[next]}
                  </Button>
                ))}
              </div>
            </div>
          )
        }
      >
        {detail && detailProfile && detailOffer && (
          <div className="space-y-4">
            <div className="rounded-[8px] border border-line bg-mist/50 px-4 py-3">
              <p className="text-[13.5px] font-medium text-navy">{detailOffer.title}</p>
              <p className="text-[12.5px] text-slate">
                {detailOffer.reference} · déposée le {formatDate(detail.appliedAt)} · CV v
                {cvOf(detail.cvId)?.versionNumber} figé au dépôt
              </p>
            </div>

            <MatchLedger match={computeMatch(detailProfile, detailOffer, skills)} compact />

            <div>
              <h3 className="text-[13px] font-semibold text-navy">Profil du candidat</h3>
              <p className="mt-1 text-[13px] text-slate">{detailProfile.headline}</p>
              <dl className="mt-2 space-y-1 text-[13px]">
                <div className="flex justify-between gap-3">
                  <dt className="text-slate">Localisation</dt>
                  <dd className="text-navy">
                    {formatPlace(detailProfile.city, detailProfile.governorate)}
                  </dd>
                </div>
                <div className="flex justify-between gap-3">
                  <dt className="text-slate">Disponibilité</dt>
                  <dd className="text-navy">{formatDate(detailProfile.availabilityDate)}</dd>
                </div>
              </dl>
            </div>

            {detail.coverLetter && (
              <div>
                <h3 className="text-[13px] font-semibold text-navy">Message du candidat</h3>
                <p className="mt-1 text-[13px] leading-relaxed text-slate">{detail.coverLetter}</p>
              </div>
            )}

            <div>
              <h3 className="mb-3 text-[13px] font-semibold text-navy">Parcours du dossier</h3>
              <StatusTimeline status={detail.status} />
            </div>

            <div>
              <h3 className="text-[13px] font-semibold text-navy">Historique</h3>
              <ol className="mt-2 space-y-1.5 text-[12.5px]">
                {[...detail.history].reverse().map((entry) => (
                  <li key={entry.id} className="flex justify-between gap-3">
                    <span className="text-navy">{STATUS_LABEL[entry.status]}</span>
                    <span className="text-slate">{formatDate(entry.changedAt)}</span>
                  </li>
                ))}
              </ol>
            </div>
          </div>
        )}
      </Modal>

      {/* Confirmation de transition */}
      <Modal
        open={pending !== null}
        onClose={() => setPending(null)}
        title={pending ? (TRANSITION_LABEL[pending.next] ?? 'Changer le statut') : ''}
        footer={
          <>
            <Button variant="secondaire" onClick={() => setPending(null)}>
              Annuler
            </Button>
            <Button variant={pending?.next === 'REJECTED' ? 'danger' : 'primaire'} onClick={runTransition}>
              {pending ? TRANSITION_LABEL[pending.next] : ''}
            </Button>
          </>
        }
      >
        <p className="text-[13.5px] leading-relaxed text-navy">
          Le dossier passera au statut « {pending ? STATUS_LABEL[pending.next] : ''} ». Le candidat verra ce changement
          et son motif dans son espace de suivi.
        </p>
        <div className="mt-4">
          <Field
            label="Motif"
            hint="Facultatif, mais visible par le candidat. Un motif précis évite une relance inutile."
          >
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
          </Field>
        </div>
        {pending?.next === 'REJECTED' && (
          <div className="mt-3">
            <Badge tone="negatif">Cette décision est définitive pour cette candidature.</Badge>
          </div>
        )}
      </Modal>
    </>
  )
}
