import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, EmptyState, Meter, Note, Panel, StatTile } from '../../components/ui'
import { ScoreDial, SkillChips } from '../../components/domain'
import { useAutoMatches } from '../../components/insights'
import { useCandidate } from '../../state/candidate'
import { useSuggestedTraining } from '../../state/candidateTraining'
import { useAuth } from '../../state/auth'
import { formatDate } from '../../lib/format'
import { matchBadge } from '../../lib/candidateOffers'
import { PROFILE_SECTION_LABEL, profileCompleteness } from '../../lib/candidateProfile'
import { STATUS_LABEL } from '../../lib/statusMachine'
import type { ApplicationStatus } from '../../lib/types'

export default function CandidatDashboard() {
  const { user } = useAuth()
  const { applications, offers, matches, records, loading, calculating, calculateMatches } = useCandidate()
  useAutoMatches()
  const active = applications.filter((item) => !['REJECTED', 'WITHDRAWN', 'HIRED'].includes(item.status))
  const best = matches
    .flatMap((match) => {
      const offer = offers.find((item) => item.id === match.offer_id)
      const badge = matchBadge(match)
      return offer && badge ? [{ offer, badge }] : []
    })
    .sort((a, b) => b.badge.score - a.badge.score)
    .slice(0, 3)
  const training = useSuggestedTraining(best.map((item) => item.offer.id), records.skills.map((item) => String(item.skill)))
  const completeness = profileCompleteness(records)
  return <>
    <PageHeader title={`Bonjour ${user?.first_name ?? ''}`} action={<Link to="/candidat/offres"><Button>Rechercher des offres</Button></Link>} />
    <PageBody className="space-y-6">
      <div className="grid gap-4 sm:grid-cols-2">
        <StatTile value={active.length} label="Candidatures en cours" note={`${applications.length} au total`} />
        <StatTile value={offers.length} label="Offres publiées" tone="teal" />
      </div>
      <Panel title="Mes meilleures correspondances" action={<Link to="/candidat/offres" className="text-teal">Toutes les offres</Link>}>
        {best.length ? <ul className="divide-y divide-line">{best.map(({ offer, badge }) => <li key={offer.id} className="flex gap-4 px-5 py-4">
          <ScoreDial score={badge.score} available />
          <div className="min-w-0 space-y-1.5 text-sm">
            <Link className="font-medium text-navy hover:text-teal" to={`/candidat/offres/${offer.id}`}>{offer.title}</Link>
            <p className="text-slate">{offer.organization_name} · {offer.city || offer.governorate}</p>
            {badge.missing.length > 0 && <p className="flex flex-wrap items-center gap-1.5 text-slate">À acquérir : <SkillChips names={badge.missing} variant="missing" /></p>}
            {training[offer.id] && <p className="text-slate">Formation suggérée : <Link className="font-medium text-teal" to="/candidat/formations">{training[offer.id].title}</Link></p>}
          </div>
        </li>)}</ul>
          : loading || calculating ? <p role="status" className="px-5 py-4 text-sm text-slate">Calcul de votre compatibilité…</p>
            : records.skills.length ? <EmptyState title="Aucune correspondance pour le moment" action={<Button size="sm" variant="secondaire" onClick={() => void calculateMatches().catch(() => {})}>Calculer ma compatibilité</Button>} />
              : <EmptyState title="Aucune compétence renseignée" action={<Link to="/candidat/profil?section=skills"><Button size="sm">Ajouter des compétences</Button></Link>}>Vos compétences servent au calcul de votre compatibilité avec les offres.</EmptyState>}
      </Panel>
      <Panel title="Mon profil" description="Indication : sections remplies sur les sections disponibles, ce n’est pas un score.">
        <div className="space-y-3 p-5 text-sm">
          <Meter value={Math.round((completeness.filled / completeness.total) * 100)} label={`${completeness.filled} sections sur ${completeness.total} remplies`} />
          {completeness.next
            ? <Note>Prochaine étape : <Link className="font-medium text-teal" to={`/candidat/profil?section=${completeness.next}`}>compléter « {PROFILE_SECTION_LABEL[completeness.next]} »</Link></Note>
            : <p className="text-slate">Toutes les sections de votre profil sont remplies.</p>}
        </div>
      </Panel>
      <Panel title="Mes candidatures" action={<Link to="/candidat/candidatures" className="text-teal">Tout voir</Link>}>
        {active.length ? <ul className="divide-y divide-line">{active.slice(0, 5).map((item) => <li key={item.id} className="px-5 py-3"><p className="font-medium text-navy">{item.offer_title}</p><p className="text-sm text-slate">Déposée le {formatDate(item.applied_at)} · {STATUS_LABEL[item.status as ApplicationStatus] ?? item.status}</p></li>)}</ul> : <EmptyState title="Aucune candidature en cours" />}
      </Panel>
    </PageBody>
  </>
}
