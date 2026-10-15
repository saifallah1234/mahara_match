import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, EmptyState, Panel, Row, Table } from '../../components/ui'
import { useStore } from '../../state/store'
import { CONTRACT_LABEL, OFFER_STATUS_LABEL, formatDate, formatPlace } from '../../lib/format'
import type { OfferStatus } from '../../lib/types'

const STATUS_TONE: Record<OfferStatus, 'positif' | 'neutre' | 'attention' | 'negatif'> = {
  PUBLISHED: 'positif',
  DRAFT: 'neutre',
  PAUSED: 'attention',
  CLOSED: 'negatif',
  ARCHIVED: 'neutre',
}

export default function RecruteurOffres() {
  const { session, offers, applications, organizationOf, closeOffer } = useStore()
  if (!session) return null

  const mine = offers
    .filter((o) => o.createdBy === session.user.id)
    .sort((a, b) => +new Date(b.publishedAt ?? 0) - +new Date(a.publishedAt ?? 0))

  return (
    <>
      <PageHeader
        title="Mes offres"
        action={
          <Link to="/recruteur/offres/nouvelle">
            <Button>Publier une offre</Button>
          </Link>
        }
      />

      <PageBody>
        <Panel>
          {mine.length === 0 ? (
            <EmptyState
              title="Aucune offre"
              action={
                <Link to="/recruteur/offres/nouvelle">
                  <Button>Créer ma première offre</Button>
                </Link>
              }
            >
              Les compétences associées à l’offre déterminent le calcul de couverture affiché aux candidats.
            </EmptyState>
          ) : (
            <Table head={['Offre', 'Entité', 'Contrat', 'Candidatures', 'Statut', '']}>
              {mine.map((offer) => {
                const count = applications.filter((a) => a.offerId === offer.id).length
                return (
                  <Row key={offer.id}>
                    <Cell>
                      <Link to={`/recruteur/offres/${offer.id}`} className="font-medium text-navy hover:text-teal">
                        {offer.title}
                      </Link>
                      <p className="text-[12.5px] text-slate">
                        {offer.reference} · {formatPlace(offer.city, offer.governorate)}
                        {offer.skills.length === 0 && ' · aucune compétence renseignée'}
                      </p>
                    </Cell>
                    <Cell className="text-[13px] text-slate">{organizationOf(offer.organizationId)?.legalName}</Cell>
                    <Cell className="text-[13px] text-slate">{CONTRACT_LABEL[offer.contractType]}</Cell>
                    <Cell className="tnum text-[13px] text-navy">{count}</Cell>
                    <Cell>
                      <Badge tone={STATUS_TONE[offer.status]}>{OFFER_STATUS_LABEL[offer.status]}</Badge>
                      {offer.applicationDeadline && offer.status === 'PUBLISHED' && (
                        <p className="mt-0.5 text-[12px] text-slate">
                          clôture {formatDate(offer.applicationDeadline)}
                        </p>
                      )}
                    </Cell>
                    <Cell className="text-right">
                      {offer.status === 'PUBLISHED' && (
                        <Button size="sm" variant="discret" onClick={() => closeOffer(offer.id)}>
                          Clôturer
                        </Button>
                      )}
                    </Cell>
                  </Row>
                )
              })}
            </Table>
          )}
        </Panel>
      </PageBody>
    </>
  )
}
