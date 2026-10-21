import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Modal, Panel, Select } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel, listStatusHistory, type RecruiterApplication, type StatusHistory } from '../../api/recruiter'
import { downloadPath } from '../../api/candidate'
import { INTERVIEW_STATUS_LABEL, INTERVIEW_TYPE_LABEL, formatDate, formatDateTime, formatTunisDateTime, labelFor } from '../../lib/format'
import { APPLICATION_FLOW, STATUS_LABEL, laterStages } from '../../lib/statusMachine'
import type { ApplicationStatus } from '../../lib/types'

const COLUMNS: ApplicationStatus[] = [...APPLICATION_FLOW, 'REJECTED', 'WITHDRAWN']
const FINAL = ['HIRED', 'REJECTED', 'WITHDRAWN']
const DECISION: Record<string, { title: string; text: string }> = {
  HIRED: { title: 'Marquer ce candidat comme recruté ?', text: 'Cette décision est définitive.' },
  REJECTED: { title: 'Refuser cette candidature ?', text: 'Cette décision est définitive.' },
}
const columnLabel = (status: string) => (status === 'WITHDRAWN' ? 'Retirées' : labelFor(STATUS_LABEL, status))

export default function RecruteurCandidatures() {
  const { offers, applications, loading, error, moveApplication } = useRecruiter()
  const [params, setParams] = useSearchParams()
  const [pending, setPending] = useState<{ id: string; status: string } | null>(null)
  const [open, setOpen] = useState<RecruiterApplication | null>(null)
  const offerId = params.get('offer') ?? ''
  const visible = offerId ? applications.filter((a) => a.offer_id === offerId) : applications
  const go = (id: string, status: string, reason?: string) => void moveApplication(id, status, reason).catch(() => {})
  const choose = (a: RecruiterApplication, status: string) => (DECISION[status] ? setPending({ id: a.id, status }) : go(a.id, status))

  return (
    <>
      <PageHeader
        title="Suivi des candidatures"
        action={
          <Select aria-label="Filtrer par offre" value={offerId} onChange={(e) => setParams(e.target.value ? { offer: e.target.value } : {})}>
            <option value="">Toutes les offres</option>
            {offers.map((o) => <option key={o.id} value={o.id}>{o.title}</option>)}
          </Select>
        }
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}

        {loading ? (
          <p className="text-slate">Chargement…</p>
        ) : applications.length === 0 ? (
          <Panel>
            <EmptyState title="Aucune candidature reçue">
              Les dossiers déposés sur vos offres apparaîtront ici.
            </EmptyState>
          </Panel>
        ) : (
          <div className="overflow-x-auto pb-2">
            <div className="flex min-w-max gap-3">
              {COLUMNS.map((status) => {
                const column = visible.filter((a) => a.status === status)
                return (
                  <section key={status} className="w-64 shrink-0">
                    <header className="mb-2 flex justify-between px-1">
                      <h2 className="text-[13px] font-semibold text-navy">{columnLabel(status)}</h2>
                      <span className="tnum text-[12px] text-slate">{column.length}</span>
                    </header>
                    <div className="min-h-24 space-y-2 rounded-[8px] bg-mist/50 p-2">
                      {column.map((a) => (
                        <div key={a.id} className="rounded-[8px] border border-line bg-white p-3 shadow-panel">
                          <button type="button" onClick={() => setOpen(a)} className="block w-full text-left">
                            <p className="text-[13.5px] font-medium text-navy">{a.offer_title}</p>
                            <p className="text-[12px] text-slate">{candidateLabel(a)} · {formatDate(a.applied_at)}</p>
                          </button>
                          {!FINAL.includes(status) && (
                            <div className="mt-2 flex items-center gap-2">
                              <Select
                                aria-label="Avancer vers"
                                value=""
                                className="h-8 py-0 text-[12px]"
                                onChange={(e) => e.target.value && choose(a, e.target.value)}
                              >
                                <option value="">Avancer…</option>
                                {laterStages(status).map((s) => <option key={s} value={s}>{labelFor(STATUS_LABEL, s)}</option>)}
                              </Select>
                              <Button size="sm" variant="danger" onClick={() => setPending({ id: a.id, status: 'REJECTED' })}>Refuser</Button>
                            </div>
                          )}
                          {status === 'REJECTED' && <Badge tone="negatif">Refusée</Badge>}
                        </div>
                      ))}
                      {column.length === 0 && <p className="px-2 py-3 text-[12px] text-slate/70">—</p>}
                    </div>
                  </section>
                )
              })}
            </div>
          </div>
        )}
        {pending && (
          <ConfirmDialog
            title={DECISION[pending.status]?.title ?? 'Refuser cette candidature ?'}
            danger={pending.status === 'REJECTED'}
            reasonLabel={pending.status === 'REJECTED' ? 'Motif (facultatif)' : undefined}
            onCancel={() => setPending(null)}
            onConfirm={(reason) => { go(pending.id, pending.status, reason || undefined); setPending(null) }}
          >
            {DECISION[pending.status]?.text ?? 'Le candidat sera informé de ce refus.'}
          </ConfirmDialog>
        )}
        {open && <ApplicationPanel application={open} onClose={() => setOpen(null)} />}
      </PageBody>
    </>
  )
}

function ApplicationPanel({ application: a, onClose }: { application: RecruiterApplication; onClose: () => void }) {
  const { interviews } = useRecruiter()
  const [history, setHistory] = useState<StatusHistory[] | null>(null)
  const [downloadError, setDownloadError] = useState('')
  useEffect(() => {
    let live = true
    listStatusHistory(a.id)
      .then((rows) => { if (live) setHistory(rows) })
      .catch(() => { if (live) setHistory([]) })
    return () => { live = false }
  }, [a.id])
  const mine = interviews.filter((i) => i.application_id === a.id)

  return (
    <Modal open onClose={onClose} title={candidateLabel(a)} footer={<Button variant="secondaire" onClick={onClose}>Fermer</Button>}>
      <div className="space-y-5 text-[13.5px]">
        <section className="space-y-1">
          <p className="text-slate">Candidature à « {a.offer_title} » · {formatDate(a.applied_at)}</p>
          <p className="text-navy">{a.applicant.email}</p>
          <Button
            size="sm"
            variant="discret"
            className="text-teal"
            onClick={() => void downloadPath(`/applications/${a.id}/cv/`, 'cv-candidat.pdf').catch((failure) => setDownloadError(failure instanceof Error ? failure.message : 'Téléchargement impossible.'))}
          >
            Télécharger le CV
          </Button>
          {downloadError && <p role="alert" className="text-coral">{downloadError}</p>}
        </section>

        {a.cover_letter && (
          <section>
            <h3 className="mb-1 font-medium text-navy">Lettre de motivation</h3>
            <p className="whitespace-pre-line text-navy">{a.cover_letter}</p>
          </section>
        )}

        <section>
          <h3 className="mb-1 font-medium text-navy">Historique</h3>
          {history === null ? (
            <p className="text-slate">Chargement…</p>
          ) : history.length === 0 ? (
            <p className="text-slate">Aucun changement de statut.</p>
          ) : (
            <ul className="space-y-1">
              {history.map((h) => (
                <li key={h.id} className="text-navy">
                  {labelFor(STATUS_LABEL, h.status)} · <span className="text-slate">{formatDateTime(h.changed_at)}</span>
                  {h.reason && <span className="text-slate"> — {h.reason}</span>}
                </li>
              ))}
            </ul>
          )}
        </section>

        <section>
          <h3 className="mb-1 font-medium text-navy">Entretiens</h3>
          {mine.length === 0 ? (
            <p className="text-slate">Aucun entretien pour cette candidature.</p>
          ) : (
            <ul className="space-y-2">
              {mine.map((i) => (
                <li key={i.id} className="text-navy">
                  {formatTunisDateTime(i.scheduled_at)} · {labelFor(INTERVIEW_TYPE_LABEL, i.type)} · {labelFor(INTERVIEW_STATUS_LABEL, i.status)}
                  {i.feedback && <p className="text-slate">{i.feedback}</p>}
                </li>
              ))}
            </ul>
          )}
        </section>
      </div>
    </Modal>
  )
}
