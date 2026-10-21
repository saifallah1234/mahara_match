import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, ConfirmDialog, EmptyState, Panel, Row, Table, Tabs } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { OFFER_STATUS_LABEL, contractLabel, formatDate } from '../../lib/format'
import type { RecruiterOffer } from '../../api/recruiter'

const TONE = { PUBLISHED: 'positif', DRAFT: 'neutre', PAUSED: 'attention', CLOSED: 'negatif', ARCHIVED: 'neutre' } as const
const TABS: { status: RecruiterOffer['status']; label: string }[] = [
  { status: 'PUBLISHED', label: 'Publiées' },
  { status: 'DRAFT', label: 'Brouillons' },
  { status: 'PAUSED', label: 'En pause' },
  { status: 'CLOSED', label: 'Clôturées' },
  { status: 'ARCHIVED', label: 'Archivées' },
]

export default function RecruteurOffres() {
  const { offers, applications, loading, error, setOfferStatus } = useRecruiter()
  const act = (o: RecruiterOffer, s: RecruiterOffer['status']) => void setOfferStatus(o.id, s).catch(() => {})
  const [closing, setClosing] = useState<RecruiterOffer | null>(null)
  const [tab, setTab] = useState<RecruiterOffer['status']>('PUBLISHED')
  const shown = offers.filter((o) => o.status === tab)

  return (
    <>
      <PageHeader
        title="Mes offres"
        action={<Link to="/recruteur/offres/nouvelle"><Button>Publier une offre</Button></Link>}
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <Panel>
          {loading ? (
            <p className="p-5 text-slate">Chargement…</p>
          ) : offers.length === 0 ? (
            <EmptyState
              title="Aucune offre"
              action={<Link to="/recruteur/offres/nouvelle"><Button>Créer ma première offre</Button></Link>}
            >
              Les compétences de l’offre servent au calcul de correspondance.
            </EmptyState>
          ) : (
            <>
              <div className="px-3 pt-2">
                <Tabs
                  tabs={TABS.map(({ status, label }) => ({
                    id: status,
                    label,
                    count: offers.filter((o) => o.status === status).length,
                  }))}
                  active={tab}
                  onChange={setTab}
                />
              </div>
              {shown.length === 0 ? (
                <EmptyState title={`Aucune offre dans « ${TABS.find((t) => t.status === tab)?.label} ».`} />
              ) : (
                <Table head={['Offre', 'Entité', 'Candidatures', 'Statut', '']}>
                  {shown.map((o) => (
                    <Row key={o.id}>
                      <Cell>
                        <Link to={`/recruteur/offres/${o.id}`} className="font-medium text-navy hover:text-teal">{o.title}</Link>
                        <p className="text-[12.5px] text-slate">{contractLabel(o.contract_type)} · {o.city || o.governorate}</p>
                      </Cell>
                      <Cell className="text-[13px] text-slate">{o.organization_name}</Cell>
                      <Cell className="tnum text-[13px] text-navy">
                        {applications.filter((a) => a.offer_id === o.id).length}
                      </Cell>
                      <Cell>
                        <Badge tone={TONE[o.status]}>{OFFER_STATUS_LABEL[o.status]}</Badge>
                        {o.application_deadline && o.status === 'PUBLISHED' && (
                          <p className="mt-0.5 text-[12px] text-slate">clôture {formatDate(o.application_deadline)}</p>
                        )}
                      </Cell>
                      <Cell className="text-right">
                        {o.status === 'DRAFT' && <Button size="sm" onClick={() => act(o, 'PUBLISHED')}>Publier</Button>}
                        {o.status === 'PUBLISHED' && <Button size="sm" variant="discret" onClick={() => setClosing(o)}>Clôturer</Button>}
                      </Cell>
                    </Row>
                  ))}
                </Table>
              )}
            </>
          )}
        </Panel>
        {closing && (
          <ConfirmDialog
            title="Clôturer cette offre ?"
            danger
            onCancel={() => setClosing(null)}
            onConfirm={() => { act(closing, 'CLOSED'); setClosing(null) }}
          >
            L’offre « {closing.title} » ne sera plus ouverte aux candidatures.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}
