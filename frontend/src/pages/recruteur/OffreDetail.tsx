import { useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Note, Panel } from '../../components/ui'
import { MatchLedger, ScoreDial, StatusPill } from '../../components/domain'
import { useStore } from '../../state/store'
import { computeMatch, rankCandidates } from '../../lib/matching'
import { CONTRACT_LABEL, EXPERIENCE_LABEL, OFFER_STATUS_LABEL, WORK_MODE_LABEL, formatDate, formatPlace, formatSalary } from '../../lib/format'

export default function RecruteurOffreDetail() {
  const { offerId } = useParams()
  const { offerOf, organizationOf, profiles, userOf, skills, applications, closeOffer } = useStore()

  const offer = offerId ? offerOf(offerId) : undefined
  if (!offer) {
    return (
      <PageBody>
        <Panel className="p-8">
          <p className="text-center text-[14px] text-slate">Cette offre est introuvable.</p>
        </Panel>
      </PageBody>
    )
  }

  const organization = organizationOf(offer.organizationId)
  const received = applications.filter((a) => a.offerId === offer.id)

  /* Recherche de candidats : seuls les profils visibles aux recruteurs
     sont proposés, conformément aux réglages de visibilité. */
  const visible = profiles.filter((p) => p.profileVisibility !== 'PRIVATE')
  const suggestions = rankCandidates(visible, offer, skills)
    .filter(({ profile }) => !received.some((a) => a.candidateId === profile.id))
    .filter(({ match }) => match.available && match.score > 0)
    .slice(0, 5)

  return (
    <>
      <PageHeader
        back={{ to: '/recruteur/offres', label: 'Mes offres' }}
        title={offer.title}
        description={`${offer.reference} · ${organization?.legalName} · ${formatPlace(offer.city, offer.governorate)}`}
        action={
          <>
            <Badge tone={offer.status === 'PUBLISHED' ? 'positif' : 'neutre'}>{OFFER_STATUS_LABEL[offer.status]}</Badge>
            {offer.status === 'PUBLISHED' && (
              <Button variant="secondaire" onClick={() => closeOffer(offer.id)}>
                Clôturer l’offre
              </Button>
            )}
          </>
        }
      />

      <PageBody className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
          <div className="space-y-6">
            <Panel title="Description">
              <p className="max-w-[68ch] px-5 py-4 text-[14px] leading-relaxed text-navy">{offer.description}</p>
            </Panel>

            <Panel
              title="Compétences demandées"
            >
              {offer.skills.length === 0 ? (
                <p className="px-5 py-4 text-[13px] text-slate">
                  Aucune compétence renseignée : les candidats voient « score indisponible ».
                </p>
              ) : (
                <ul className="divide-y divide-line/70">
                  {offer.skills.map((entry) => (
                    <li key={entry.skillId} className="flex items-center justify-between px-5 py-3 text-[13.5px]">
                      <span className="font-medium text-navy">
                        {skills.find((s) => s.id === entry.skillId)?.canonicalName}
                      </span>
                      <span className="text-slate">
                        {entry.importance === 'OBLIGATOIRE' ? 'Obligatoire · poids 2' : 'Souhaitée · poids 1'}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="Candidatures reçues" description={`${received.length} dossier${received.length > 1 ? 's' : ''}`}>
              {received.length === 0 ? (
                <EmptyState title="Aucune candidature pour l’instant" />
              ) : (
                <ul className="divide-y divide-line/70">
                  {received.map((application) => {
                    const profile = profiles.find((p) => p.id === application.candidateId)
                    const user = profile ? userOf(profile.userId) : undefined
                    if (!profile) return null
                    const match = computeMatch(profile, offer, skills)
                    return (
                      <li key={application.id} className="flex items-center gap-4 px-5 py-3.5">
                        <ScoreDial score={match.score} available={match.available} size={42} />
                        <div className="min-w-0 flex-1">
                          <p className="text-[14px] font-medium text-navy">
                            {user?.firstName} {user?.lastName}
                          </p>
                          <p className="text-[12.5px] text-slate">
                            {profile.headline} · déposée le {formatDate(application.appliedAt)}
                          </p>
                        </div>
                        <StatusPill status={application.status} />
                      </li>
                    )
                  })}
                </ul>
              )}
            </Panel>

            <Panel
              title="Candidats suggérés"
              description="Profils visibles aux recruteurs qui n’ont pas encore postulé, classés par couverture."
            >
              {suggestions.length === 0 ? (
                <EmptyState title="Aucun profil correspondant">
                  Seuls les profils dont la visibilité autorise la consultation par les recruteurs apparaissent ici.
                </EmptyState>
              ) : (
                <ul className="divide-y divide-line/70">
                  {suggestions.map(({ profile, match }) => {
                    const user = userOf(profile.userId)
                    return (
                      <li key={profile.id} className="flex items-center gap-4 px-5 py-3.5">
                        <ScoreDial score={match.score} available={match.available} size={42} />
                        <div className="min-w-0 flex-1">
                          <p className="text-[14px] font-medium text-navy">
                            {user?.firstName} {user?.lastName}
                          </p>
                          <p className="text-[12.5px] text-slate">
                            {profile.headline} · {formatPlace(profile.city, profile.governorate)}
                          </p>
                        </div>
                      </li>
                    )
                  })}
                </ul>
              )}
            </Panel>
          </div>

          <div className="space-y-4">
            <Panel title="Informations">
              <dl className="divide-y divide-line/70 text-[13.5px]">
                {[
                  ['Contrat', CONTRACT_LABEL[offer.contractType]],
                  ['Mode de travail', WORK_MODE_LABEL[offer.workMode]],
                  ['Expérience', EXPERIENCE_LABEL[offer.experienceLevel]],
                  ['Rémunération', formatSalary(offer.minSalary, offer.maxSalary)],
                  ['Publiée le', formatDate(offer.publishedAt)],
                  ['Clôture', offer.applicationDeadline ? formatDate(offer.applicationDeadline) : 'Non renseignée'],
                  ['Candidature', offer.easyApply ? 'Sur la plateforme' : 'Site de l’entreprise'],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-baseline justify-between gap-4 px-5 py-2.5">
                    <dt className="shrink-0 text-slate">{label}</dt>
                    <dd className="text-right font-medium text-navy">{value}</dd>
                  </div>
                ))}
              </dl>
            </Panel>

            {offer.sourceId && (
              <Note tone="attention">
                Cette offre provient d’un import automatique (identifiant externe {offer.externalId}). Les
                modifications locales peuvent être écrasées au prochain lot.
              </Note>
            )}

            {received.length > 0 && (
              <Panel title="Exemple de calcul">
                <div className="p-4">
                  {(() => {
                    const first = received[0]
                    const profile = profiles.find((p) => p.id === first.candidateId)
                    if (!profile) return null
                    return <MatchLedger match={computeMatch(profile, offer, skills)} compact />
                  })()}
                </div>
              </Panel>
            )}
          </div>
        </div>
      </PageBody>
    </>
  )
}
