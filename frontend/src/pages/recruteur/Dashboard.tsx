import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, EmptyState, Panel, StatTile } from '../../components/ui'
import { useAuth } from '../../state/auth'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel } from '../../api/recruiter'
import { formatDate } from '../../lib/format'

const FINAL = ['HIRED', 'REJECTED', 'WITHDRAWN']

export default function RecruteurDashboard() {
  const { workspace } = useAuth()
  const { offers, applications, interviews, loading, error } = useRecruiter()

  const published = offers.filter((o) => o.status === 'PUBLISHED')
  const toReview = applications.filter((a) => a.status === 'SUBMITTED')
  const inProgress = applications.filter((a) => !FINAL.includes(a.status))
  const upcoming = interviews.filter((i) => i.status === 'SCHEDULED')

  return (
    <>
      <PageHeader
        title={workspace?.organization?.legal_name ?? 'Espace recruteur'}
        action={<Link to="/recruteur/offres/nouvelle"><Button>Publier une offre</Button></Link>}
      />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {loading && <p className="text-slate">Chargement…</p>}

        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={published.length} label="Offres publiées" note={`${offers.length} au total`} />
          <StatTile value={toReview.length} label="Dossiers à examiner" tone="coral" note="au statut « Soumise »" />
          <StatTile value={inProgress.length} label="Candidatures en cours" tone="teal" />
          <StatTile value={upcoming.length} label="Entretiens planifiés" tone="leaf" />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <Panel
            title="Dossiers à examiner"
            description="Les candidatures en attente d’une première lecture."
            action={<Link to="/recruteur/candidatures" className="text-[13px] font-medium text-teal hover:underline">Ouvrir le suivi des candidatures</Link>}
          >
            {toReview.length === 0 ? (
              <EmptyState title="Aucun dossier en attente">
                Les nouvelles candidatures apparaîtront ici dès leur dépôt.
              </EmptyState>
            ) : (
              <ul className="divide-y divide-line/70">
                {toReview.slice(0, 6).map((a) => (
                  <li key={a.id} className="flex items-center justify-between gap-4 px-5 py-3.5">
                    <div className="min-w-0">
                      <p className="text-[14px] font-medium text-navy">{a.offer_title}</p>
                      <p className="text-[12.5px] text-slate">{candidateLabel(a)} · déposée le {formatDate(a.applied_at)}</p>
                    </div>
                    <Link to="/recruteur/candidatures"><Button size="sm" variant="secondaire">Examiner</Button></Link>
                  </li>
                ))}
              </ul>
            )}
          </Panel>

          <Panel title="Mes offres">
            {offers.length === 0 ? (
              <EmptyState title="Aucune offre créée" />
            ) : (
              <ul className="divide-y divide-line/70">
                {offers.slice(0, 6).map((o) => {
                  const count = applications.filter((a) => a.offer_id === o.id).length
                  return (
                    <li key={o.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                      <div className="min-w-0">
                        <Link to={`/recruteur/offres/${o.id}`} className="text-[14px] font-medium text-navy hover:text-teal">{o.title}</Link>
                        <p className="text-[12.5px] text-slate">{count} candidature{count > 1 ? 's' : ''}</p>
                      </div>
                      <span className="shrink-0 text-[12.5px] text-slate">
                        {o.status === 'PUBLISHED' && o.application_deadline ? `clôture ${formatDate(o.application_deadline)}`
                          : o.status === 'DRAFT' ? 'brouillon' : o.status === 'CLOSED' ? 'clôturée' : ''}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}
          </Panel>
        </div>
      </PageBody>
    </>
  )
}