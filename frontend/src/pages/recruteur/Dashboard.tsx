import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, EmptyState, Panel, StatTile } from '../../components/ui'
import { ScoreDial, StatusPill } from '../../components/domain'
import { useStore } from '../../state/store'
import { computeMatch } from '../../lib/matching'
import { isTerminal } from '../../lib/statusMachine'
import { formatDate, relativeDays } from '../../lib/format'

export default function RecruteurDashboard() {
  const { session, offers, applications, profileOf, userOf, skills, organizationOf, interviews } = useStore()
  if (!session) return null

  const orgId = session.user.organizationId
  const org = organizationOf(orgId)
  const myOffers = offers.filter((o) => o.createdBy === session.user.id)
  const published = myOffers.filter((o) => o.status === 'PUBLISHED')
  const received = applications.filter((a) => myOffers.some((o) => o.id === a.offerId))
  const toReview = received.filter((a) => a.status === 'SUBMITTED')
  const inProgress = received.filter((a) => !isTerminal(a.status))
  const upcoming = interviews.filter((i) => i.status === 'PLANIFIE')

  return (
    <>
      <PageHeader
        title={org?.legalName ?? 'Espace recruteur'}
        action={
          <Link to="/recruteur/offres/nouvelle">
            <Button>Publier une offre</Button>
          </Link>
        }
      />

      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={published.length} label="Offres publiées" note={`${myOffers.length} au total`} />
          <StatTile value={toReview.length} label="Dossiers à examiner" tone="coral" note="au statut « Soumise »" />
          <StatTile value={inProgress.length} label="Candidatures en cours" tone="teal" />
          <StatTile value={upcoming.length} label="Entretiens planifiés" tone="leaf" />
        </div>

        <div className="grid gap-6 lg:grid-cols-[1.2fr_1fr]">
          <Panel
            title="Dossiers à examiner"
            description="Les candidatures en attente d’une première lecture."
            action={
              <Link to="/recruteur/candidatures" className="text-[13px] font-medium text-teal hover:underline">
                Ouvrir le pipeline
              </Link>
            }
          >
            {toReview.length === 0 ? (
              <EmptyState title="Aucun dossier en attente">
                Les nouvelles candidatures apparaîtront ici dès leur dépôt.
              </EmptyState>
            ) : (
              <ul className="divide-y divide-line/70">
                {toReview.map((application) => {
                  const profile = profileOf(application.candidateId)
                  const offer = offers.find((o) => o.id === application.offerId)
                  const user = profile ? userOf(profile.userId) : undefined
                  if (!profile || !offer) return null
                  const match = computeMatch(profile, offer, skills)
                  return (
                    <li key={application.id} className="flex items-center gap-4 px-5 py-3.5">
                      <ScoreDial score={match.score} available={match.available} size={44} />
                      <div className="min-w-0 flex-1">
                        <p className="text-[14px] font-medium text-navy">
                          {user?.firstName} {user?.lastName}
                        </p>
                        <p className="text-[12.5px] text-slate">
                          {offer.title} · déposée {relativeDays(application.appliedAt)}
                        </p>
                      </div>
                      <Link to="/recruteur/candidatures">
                        <Button size="sm" variant="secondaire">
                          Examiner
                        </Button>
                      </Link>
                    </li>
                  )
                })}
              </ul>
            )}
          </Panel>

          <Panel title="Mes offres">
            {myOffers.length === 0 ? (
              <EmptyState title="Aucune offre créée" />
            ) : (
              <ul className="divide-y divide-line/70">
                {myOffers.slice(0, 6).map((offer) => {
                  const count = applications.filter((a) => a.offerId === offer.id).length
                  return (
                    <li key={offer.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                      <div className="min-w-0">
                        <Link to={`/recruteur/offres/${offer.id}`} className="text-[14px] font-medium text-navy hover:text-teal">
                          {offer.title}
                        </Link>
                        <p className="text-[12.5px] text-slate">
                          {offer.reference} · {count} candidature{count > 1 ? 's' : ''}
                        </p>
                      </div>
                      <span className="shrink-0 text-[12.5px] text-slate">
                        {offer.status === 'PUBLISHED' && offer.applicationDeadline
                          ? `clôture ${formatDate(offer.applicationDeadline)}`
                          : offer.status === 'DRAFT'
                            ? 'brouillon'
                            : offer.status === 'CLOSED'
                              ? 'clôturée'
                              : ''}
                      </span>
                    </li>
                  )
                })}
              </ul>
            )}
          </Panel>
        </div>

        <Panel title="Activité récente">
          <ul className="divide-y divide-line/70">
            {received
              .flatMap((a) =>
                a.history.slice(-1).map((h) => ({ application: a, entry: h })),
              )
              .sort((a, b) => +new Date(b.entry.changedAt) - +new Date(a.entry.changedAt))
              .slice(0, 6)
              .map(({ application, entry }) => {
                const profile = profileOf(application.candidateId)
                const user = profile ? userOf(profile.userId) : undefined
                const offer = offers.find((o) => o.id === application.offerId)
                return (
                  <li key={entry.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                    <p className="text-[13.5px] text-navy">
                      <span className="font-medium">
                        {user?.firstName} {user?.lastName}
                      </span>{' '}
                      — {offer?.title}
                    </p>
                    <div className="flex items-center gap-3">
                      <StatusPill status={entry.status} />
                      <span className="text-[12.5px] text-slate">{relativeDays(entry.changedAt)}</span>
                    </div>
                  </li>
                )
              })}
          </ul>
        </Panel>
      </PageBody>
    </>
  )
}
