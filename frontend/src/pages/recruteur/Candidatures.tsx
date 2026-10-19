import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Panel } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel } from '../../api/recruiter'
import { downloadPath } from '../../api/candidate'
import { formatDate } from '../../lib/format'

const FLOW = ['SUBMITTED', 'UNDER_REVIEW', 'PRESELECTED', 'INTERVIEW', 'OFFERED', 'HIRED']
const COLUMNS = [...FLOW, 'REJECTED']
const LABEL: Record<string, string> = {
  SUBMITTED: 'Soumise', UNDER_REVIEW: 'En examen', PRESELECTED: 'Présélectionnée', INTERVIEW: 'Entretien',
  OFFERED: 'Proposée', HIRED: 'Recrutée', REJECTED: 'Refusée', WITHDRAWN: 'Retirée',
}
const FINAL = ['HIRED', 'REJECTED', 'WITHDRAWN']

export default function RecruteurCandidatures() {
  const { applications, loading, error, moveApplication } = useRecruiter()
  const go = (id: string, status: string) => void moveApplication(id, status).catch(() => {})

  return (
    <>
      <PageHeader title="Candidatures reçues" />
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
                const column = applications.filter((a) => a.status === status)
                const next = FLOW[FLOW.indexOf(status) + 1]
                return (
                  <section key={status} className="w-64 shrink-0">
                    <header className="mb-2 flex justify-between px-1">
                      <h2 className="text-[13px] font-semibold text-navy">{LABEL[status]}</h2>
                      <span className="tnum text-[12px] text-slate">{column.length}</span>
                    </header>
                    <div className="min-h-24 space-y-2 rounded-[8px] bg-mist/50 p-2">
                      {column.map((a) => (
                        <div key={a.id} className="rounded-[8px] border border-line bg-white p-3 shadow-panel">
                          <p className="text-[13.5px] font-medium text-navy">{a.offer_title}</p>
                          <p className="text-[12px] text-slate">{candidateLabel(a)} · {formatDate(a.applied_at)}</p>
                          <button
                            className="mt-1 text-[12px] font-medium text-teal hover:underline"
                            onClick={() => void downloadPath(`/applications/${a.id}/cv/`, 'cv-candidat.pdf').catch(() => {})}
                          >
                            Télécharger le CV
                          </button>
                          {!FINAL.includes(status) && (
                            <div className="mt-2 flex gap-2">
                              {next && <Button size="sm" onClick={() => go(a.id, next)}>{LABEL[next]}</Button>}
                              <Button size="sm" variant="danger" onClick={() => go(a.id, 'REJECTED')}>Refuser</Button>
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
      </PageBody>
    </>
  )
}