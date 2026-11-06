import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, EmptyState, Panel, StatTile } from '../../components/ui'
import { useCandidate } from '../../state/candidate'
import { useAuth } from '../../state/auth'
import { formatDate } from '../../lib/format'
import { STATUS_LABEL } from '../../lib/statusMachine'
import type { ApplicationStatus } from '../../lib/types'

export default function CandidatDashboard() {
  const { user } = useAuth()
  const { applications, offers } = useCandidate()
  const active = applications.filter((item) => !['REJECTED', 'WITHDRAWN', 'HIRED'].includes(item.status))
  return <>
    <PageHeader title={`Bonjour ${user?.first_name ?? ''}`} action={<Link to="/candidat/offres"><Button>Rechercher des offres</Button></Link>} />
    <PageBody className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatTile value={active.length} label="Candidatures en cours" note={`${applications.length} au total`} />
        <StatTile value={offers.length} label="Offres publiées" tone="teal" />
      </div>
      <Panel title="Mes candidatures" action={<Link to="/candidat/candidatures" className="text-teal">Tout voir</Link>}>
        {active.length ? <ul className="divide-y divide-line">{active.slice(0, 5).map((item) => <li key={item.id} className="px-5 py-3"><p className="font-medium text-navy">{item.offer_title}</p><p className="text-sm text-slate">Déposée le {formatDate(item.applied_at)} · {STATUS_LABEL[item.status as ApplicationStatus] ?? item.status}</p></li>)}</ul> : <EmptyState title="Aucune candidature en cours" />}
      </Panel>
      <Panel title="Offres publiées" action={<Link to="/candidat/offres" className="text-teal">Toutes les offres</Link>}>
        {offers.length ? <ul className="divide-y divide-line">{offers.slice(0, 5).map((offer) => <li key={offer.id} className="px-5 py-3"><Link className="font-medium text-navy hover:text-teal" to={`/candidat/offres/${offer.id}`}>{offer.title}</Link><p className="text-sm text-slate">{offer.organization_name} · {offer.governorate}</p></li>)}</ul> : <EmptyState title="Aucune offre publiée" />}
      </Panel>
    </PageBody>
  </>
}
