import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, EmptyState, Field, Modal, Panel, Tabs, Textarea } from '../../components/ui'
import { StatusPill, StatusTimeline } from '../../components/domain'
import { useStore } from '../../state/store'
import { STATUS_LABEL, allowedTransitions, isTerminal } from '../../lib/statusMachine'
import { formatDate, formatDateTime, formatPlace, relativeDays } from '../../lib/format'

type Tab = 'encours' | 'cloturees'

export default function CandidatCandidatures() {
  const { currentProfile, applications, offerOf, organizationOf, cvOf, transition, interviews } = useStore()
  const [tab, setTab] = useState<Tab>('encours')
  const [withdrawing, setWithdrawing] = useState<string | null>(null)
  const [reason, setReason] = useState('')

  if (!currentProfile) return null

  const mine = applications
    .filter((a) => a.candidateId === currentProfile.id)
    .sort((a, b) => +new Date(b.appliedAt) - +new Date(a.appliedAt))

  const active = mine.filter((a) => !isTerminal(a.status))
  const closed = mine.filter((a) => isTerminal(a.status))
  const shown = tab === 'encours' ? active : closed

  function confirmWithdraw() {
    if (!withdrawing) return
    transition(withdrawing, 'WITHDRAWN', reason || undefined)
    setWithdrawing(null)
    setReason('')
  }

  return (
    <>
      <PageHeader
        title="Mes candidatures"
      />

      <PageBody className="space-y-5">
        <Tabs<Tab>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'encours', label: 'En cours', count: active.length },
            { id: 'cloturees', label: 'Clôturées', count: closed.length },
          ]}
        />

        {shown.length === 0 ? (
          <Panel>
            <EmptyState
              title={tab === 'encours' ? 'Aucune candidature en cours' : 'Aucune candidature clôturée'}
              action={
                tab === 'encours' ? (
                  <Link to="/candidat/offres">
                    <Button>Voir les offres ouvertes</Button>
                  </Link>
                ) : undefined
              }
            >
              {tab === 'encours' && 'Les offres sont classées selon la couverture de vos compétences confirmées.'}
            </EmptyState>
          </Panel>
        ) : (
          <div className="space-y-4">
            {shown.map((application) => {
              const offer = offerOf(application.offerId)
              const cv = cvOf(application.cvId)
              if (!offer) return null
              const canWithdraw = allowedTransitions(application.status, 'CANDIDATE').includes('WITHDRAWN')
              const relatedInterviews = interviews.filter((i) => i.applicationId === application.id)

              return (
                <Panel key={application.id}>
                  <div className="flex flex-wrap items-start justify-between gap-4 border-b border-line px-5 py-4">
                    <div className="min-w-0">
                      <Link
                        to={`/candidat/offres/${offer.id}`}
                        className="text-[15px] font-semibold text-navy hover:text-teal"
                      >
                        {offer.title}
                      </Link>
                      <p className="mt-0.5 text-[13px] text-slate">
                        {organizationOf(offer.organizationId)?.legalName} · {formatPlace(offer.city, offer.governorate)}
                      </p>
                      <p className="mt-1 text-[12.5px] text-slate">
                        Déposée {relativeDays(application.appliedAt)} · CV v{cv?.versionNumber} transmis
                      </p>
                    </div>
                    <div className="flex shrink-0 items-center gap-2">
                      <StatusPill status={application.status} />
                      {canWithdraw && (
                        <Button size="sm" variant="discret" onClick={() => setWithdrawing(application.id)}>
                          Retirer
                        </Button>
                      )}
                    </div>
                  </div>

                  <div className="border-b border-line px-5 py-5">
                    <StatusTimeline status={application.status} />
                  </div>

                  {relatedInterviews.length > 0 && (
                    <div className="border-b border-line bg-mist/40 px-5 py-3.5">
                      {relatedInterviews.map((interview) => (
                        <p key={interview.id} className="text-[13.5px] text-navy">
                          Entretien {interview.type.toLowerCase()} le {formatDateTime(interview.scheduledAt)} ·{' '}
                          {interview.durationMinutes} min · {interview.locationOrUrl}
                        </p>
                      ))}
                    </div>
                  )}

                  <div className="px-5 py-4">
                    <h3 className="text-[13px] font-semibold text-navy">Historique du dossier</h3>
                    <ol className="mt-3 space-y-2.5">
                      {[...application.history].reverse().map((entry) => (
                        <li key={entry.id} className="flex gap-3 text-[13px]">
                          <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-line" />
                          <div>
                            <p className="text-navy">
                              <span className="font-medium">{STATUS_LABEL[entry.status]}</span>
                              <span className="text-slate"> · {formatDate(entry.changedAt)}</span>
                            </p>
                            {entry.reason && <p className="mt-0.5 text-slate">{entry.reason}</p>}
                          </div>
                        </li>
                      ))}
                    </ol>
                  </div>

                  {application.coverLetter && (
                    <div className="border-t border-line px-5 py-4">
                      <h3 className="text-[13px] font-semibold text-navy">Message transmis</h3>
                      <p className="mt-1.5 max-w-[68ch] text-[13.5px] leading-relaxed text-slate">
                        {application.coverLetter}
                      </p>
                    </div>
                  )}
                </Panel>
              )
            })}
          </div>
        )}

      </PageBody>

      <Modal
        open={withdrawing !== null}
        onClose={() => setWithdrawing(null)}
        title="Retirer ma candidature"
        footer={
          <>
            <Button variant="secondaire" onClick={() => setWithdrawing(null)}>
              Garder ma candidature
            </Button>
            <Button variant="danger" onClick={confirmWithdraw}>
              Retirer la candidature
            </Button>
          </>
        }
      >
        <p className="text-[13.5px] leading-relaxed text-navy">
          Le recruteur verra que le dossier a été retiré. L’historique est conservé et le retrait est définitif pour
          cette candidature.
        </p>
        <div className="mt-4">
          <Field label="Motif" hint="Facultatif. Il apparaîtra dans l’historique du dossier.">
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} rows={3} />
          </Field>
        </div>
      </Modal>
    </>
  )
}
