import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Meter, Note, Panel, StatTile } from '../../components/ui'
import { MatchLedger, OfferCard, StatusPill } from '../../components/domain'
import { useStore } from '../../state/store'
import { computeMatch, headlineMatch, rankOffers, skillGaps } from '../../lib/matching'
import { isTerminal } from '../../lib/statusMachine'
import { formatDate, relativeDays } from '../../lib/format'

export default function CandidatDashboard() {
  const { currentProfile, offers, applications, skills, organizationOf, programs, sessions, enrollments, userOf } =
    useStore()
  if (!currentProfile) return null

  const mine = applications.filter((a) => a.candidateId === currentProfile.id)
  const active = mine.filter((a) => !isTerminal(a.status))
  const ranked = rankOffers(currentProfile, offers, skills).filter(
    (r) => !mine.some((a) => a.offerId === r.offer.id && a.status !== 'WITHDRAWN'),
  )
  const gaps = skillGaps(currentProfile, offers, skills).slice(0, 4)
  const best = headlineMatch(ranked)
  const myEnrollments = enrollments.filter((e) => e.candidateId === currentProfile.id)
  const user = userOf(currentProfile.userId)

  const unvalidated = currentProfile.skills.filter((s) => !s.validated)

  return (
    <>
      <PageHeader
        title={`Bonjour ${user?.firstName ?? ''}`}
        action={
          <Link to="/candidat/offres">
            <Button>Rechercher des offres</Button>
          </Link>
        }
      />

      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={active.length} label="Candidatures en cours" note={`${mine.length} au total`} />
          <StatTile value={ranked.length} label="Offres ouvertes à découvrir" tone="teal" />
          <StatTile value={gaps.length} label="Compétences à développer" note="repérées sur les offres ouvertes" tone="coral" />
          <StatTile value={myEnrollments.length} label="Formations suivies" tone="leaf" />
        </div>

        {currentProfile.completionScore < 100 && (
          <Panel className="p-5">
            <div className="flex flex-wrap items-center justify-between gap-4">
              <div className="min-w-0 flex-1">
                <h2 className="text-[15px] font-semibold text-navy">Complétude de votre profil</h2>
                <p className="mt-0.5 text-[13px] text-slate">
                  Un profil complet améliore la précision des correspondances et la visibilité auprès des recruteurs.
                </p>
                <div className="mt-3 max-w-md">
                  <Meter value={currentProfile.completionScore} label="Profil renseigné" />
                </div>
              </div>
              <Link to="/candidat/profil">
                <Button variant="secondaire">Compléter mon profil</Button>
              </Link>
            </div>
          </Panel>
        )}

        {unvalidated.length > 0 && (
          <Note tone="attention">
            {unvalidated.length === 1
              ? 'Une compétence est déclarée mais pas encore confirmée.'
              : `${unvalidated.length} compétences sont déclarées mais pas encore confirmées.`}{' '}
            Tant qu’elles ne le sont pas, elles ne comptent pas dans vos scores de correspondance.{' '}
            <Link to="/candidat/profil" className="font-medium text-teal underline underline-offset-2">
              Les confirmer
            </Link>
          </Note>
        )}

        <div className="grid gap-6 lg:grid-cols-[1.3fr_1fr]">
          <div className="space-y-6">
            {best && (
              <Panel
                title="Votre meilleure correspondance"
                description={`${best.offer.title} — ${organizationOf(best.offer.organizationId)?.legalName ?? ''}`}
                action={
                  <Link to={`/candidat/offres/${best.offer.id}`}>
                    <Button size="sm" variant="secondaire">
                      Voir l’offre
                    </Button>
                  </Link>
                }
              >
                <div className="p-5">
                  <MatchLedger match={computeMatch(currentProfile, best.offer, skills)} compact />
                </div>
              </Panel>
            )}

            <Panel
              title="Mes candidatures en cours"
              action={
                <Link to="/candidat/candidatures" className="text-[13px] font-medium text-teal hover:underline">
                  Tout voir
                </Link>
              }
            >
              {active.length === 0 ? (
                <EmptyState title="Aucune candidature en cours">
                  Les offres recommandées ci-contre sont classées par couverture de vos compétences confirmées.
                </EmptyState>
              ) : (
                <ul className="divide-y divide-line/70">
                  {active.map((application) => {
                    const offer = offers.find((o) => o.id === application.offerId)
                    if (!offer) return null
                    return (
                      <li key={application.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                        <div className="min-w-0">
                          <Link to="/candidat/candidatures" className="text-[14px] font-medium text-navy hover:text-teal">
                            {offer.title}
                          </Link>
                          <p className="text-[12.5px] text-slate">
                            {organizationOf(offer.organizationId)?.legalName} · déposée {relativeDays(application.appliedAt)}
                          </p>
                        </div>
                        <StatusPill status={application.status} />
                      </li>
                    )
                  })}
                </ul>
              )}
            </Panel>
          </div>

          <div className="space-y-6">
            <Panel title="Compétences à développer" description="Repérées sur les offres ouvertes qui vous correspondent.">
              {gaps.length === 0 ? (
                <EmptyState title="Aucun écart identifié">
                  Vos compétences confirmées couvrent les offres ouvertes consultées.
                </EmptyState>
              ) : (
                <ul className="divide-y divide-line/70">
                  {gaps.map((gap) => {
                    const linked = programs.filter((p) => p.status === 'PUBLISHED' && p.skillIds.includes(gap.skillId))
                    return (
                      <li key={gap.skillId} className="px-5 py-3.5">
                        <div className="flex items-center justify-between gap-3">
                          <span className="text-[14px] font-medium text-navy">{gap.skillName}</span>
                          <Badge tone={gap.mandatoryCount > 0 ? 'negatif' : 'attention'}>
                            {gap.demandCount} offre{gap.demandCount > 1 ? 's' : ''}
                          </Badge>
                        </div>
                        <p className="mt-1 text-[12.5px] text-slate">
                          {linked.length > 0
                            ? `${linked.length} formation${linked.length > 1 ? 's' : ''} enseigne${linked.length > 1 ? 'nt' : ''} cette compétence.`
                            : 'Aucune formation correspondante n’a été trouvée.'}
                        </p>
                        {linked.length > 0 && (
                          <Link
                            to="/candidat/formations"
                            className="mt-1.5 inline-block text-[12.5px] font-medium text-teal hover:underline"
                          >
                            Voir les formations
                          </Link>
                        )}
                      </li>
                    )
                  })}
                </ul>
              )}
            </Panel>

            {myEnrollments.length > 0 && (
              <Panel title="Mes formations">
                <ul className="divide-y divide-line/70">
                  {myEnrollments.map((enrollment) => {
                    const trainingSession = sessions.find((s) => s.id === enrollment.sessionId)
                    const program = programs.find((p) => p.id === trainingSession?.programId)
                    if (!program || !trainingSession) return null
                    return (
                      <li key={enrollment.id} className="px-5 py-3.5">
                        <p className="text-[14px] font-medium text-navy">{program.title}</p>
                        <p className="mt-0.5 text-[12.5px] text-slate">
                          Du {formatDate(trainingSession.startDate)} au {formatDate(trainingSession.endDate)}
                        </p>
                        <div className="mt-2">
                          <Meter value={enrollment.completionRate} label="Progression" tone="leaf" />
                        </div>
                      </li>
                    )
                  })}
                </ul>
              </Panel>
            )}
          </div>
        </div>

        <Panel title="Offres recommandées" description="Classées par couverture de vos compétences confirmées.">
          {ranked.length === 0 ? (
            <EmptyState title="Aucune offre ouverte ne correspond pour l’instant" />
          ) : (
            <div className="grid gap-3 p-5 sm:grid-cols-2">
              {ranked.slice(0, 4).map(({ offer, match }) => (
                <OfferCard
                  key={offer.id}
                  offer={offer}
                  organizationName={organizationOf(offer.organizationId)?.legalName ?? '—'}
                  match={match}
                  to={`/candidat/offres/${offer.id}`}
                />
              ))}
            </div>
          )}
        </Panel>
      </PageBody>
    </>
  )
}
