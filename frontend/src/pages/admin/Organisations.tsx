import { PageBody, PageHeader } from '../../components/layout'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Button, Cell, ConfirmDialog, EmptyState, Loading, Panel, Row, Select, Table } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import { ORGANIZATION_STATUS_LABEL, ORGANIZATION_TYPE_LABEL, filterOrganizations } from '../../lib/adminFilters'
import { labelFor } from '../../lib/format'

const TONE = { PENDING: 'attention', VERIFIED: 'positif', REJECTED: 'negatif' } as const

export default function AdminOrganisations() {
  const { organizations, loading, error, verify, reject } = useAdmin()
  const [rejecting, setRejecting] = useState<(typeof organizations)[number] | null>(null)
  const [status, setStatus] = useState('')
  const [type, setType] = useState('')
  const shown = filterOrganizations(organizations, { status, type })
  // Le compteur reprend la liste complète, comme la tuile du tableau de bord.
  const pending = organizations.filter((o) => o.verification_status === 'PENDING').length
  return (
    <>
      <PageHeader
        title="Organisations"
        action={
          <div className="flex flex-wrap gap-2">
            <Select value={status} onChange={(e) => setStatus(e.target.value)} className="min-w-44" aria-label="Statut">
              <option value="">Tous les statuts</option>
              {Object.entries(ORGANIZATION_STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
            <Select value={type} onChange={(e) => setType(e.target.value)} className="min-w-52" aria-label="Type">
              <option value="">Tous les types</option>
              {Object.entries(ORGANIZATION_TYPE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
          </div>
        }
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <p className="mb-3 text-[13px] text-slate">{pending} organisation(s) en attente de vérification.</p>
        <Panel>
          {loading ? <Loading /> : shown.length === 0 ? (
            <EmptyState title="Aucune organisation ne correspond.">Modifiez la recherche ou les filtres.</EmptyState>
          ) : (
            <Table head={['Organisation', 'Type', 'Matricule fiscal', 'Lieu', 'Statut', '']}>
              {shown.map((o) => (
                <Row key={o.id}>
                  <Cell className="font-medium text-navy"><Link to={`/admin/organisations/${o.id}`} className="hover:text-teal hover:underline">{o.legal_name}</Link></Cell>
                  <Cell className="text-[13px]">{labelFor(ORGANIZATION_TYPE_LABEL, o.type, 'Autre type')}</Cell>
                  <Cell className="tnum text-[13px] text-slate">{o.matricule_fiscal}</Cell>
                  <Cell className="text-[13px] text-slate">{[o.city, o.governorate].filter(Boolean).join(', ') || '—'}</Cell>
                  <Cell><Badge tone={TONE[o.verification_status]}>{ORGANIZATION_STATUS_LABEL[o.verification_status]}</Badge></Cell>
                  <Cell className="text-right">
                    {o.verification_status !== 'VERIFIED' && <Button size="sm" onClick={() => void verify(o.id).catch(() => {})}>Vérifier</Button>}{' '}
                    {o.verification_status === 'PENDING' && <Button size="sm" variant="danger" onClick={() => setRejecting(o)}>Rejeter</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
        {rejecting && (
          <ConfirmDialog
            title="Rejeter cette organisation ?"
            danger
            onCancel={() => setRejecting(null)}
            onConfirm={() => { void reject(rejecting.id).catch(() => {}); setRejecting(null) }}
          >
            L’organisation {rejecting.legal_name} sera marquée comme rejetée.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}
