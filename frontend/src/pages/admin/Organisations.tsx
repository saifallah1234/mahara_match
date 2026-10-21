import { PageBody, PageHeader } from '../../components/layout'
import { useState } from 'react'
import { Badge, Button, Cell, ConfirmDialog, Panel, Row, Table } from '../../components/ui'
import { useAdmin } from '../../state/admin'

const TYPE: Record<string, string> = {
  COMPANY: 'Entreprise', SUBSIDIARY: 'Filiale', TRAINING_PROVIDER: 'Organisme de formation', ANETI: 'ANETI', MINISTRY: 'Ministère',
}
const STATUS = { PENDING: 'En attente', VERIFIED: 'Vérifiée', REJECTED: 'Rejetée' } as const
const TONE = { PENDING: 'attention', VERIFIED: 'positif', REJECTED: 'negatif' } as const

export default function AdminOrganisations() {
  const { organizations, loading, error, verify, reject } = useAdmin()
  const [rejecting, setRejecting] = useState<(typeof organizations)[number] | null>(null)
  return (
    <>
      <PageHeader title="Organisations" />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : (
            <Table head={['Organisation', 'Type', 'Matricule fiscal', 'Lieu', 'Statut', '']}>
              {organizations.map((o) => (
                <Row key={o.id}>
                  <Cell className="font-medium text-navy">{o.legal_name}</Cell>
                  <Cell className="text-[13px]">{TYPE[o.type] ?? o.type}</Cell>
                  <Cell className="tnum text-[13px] text-slate">{o.matricule_fiscal}</Cell>
                  <Cell className="text-[13px] text-slate">{[o.city, o.governorate].filter(Boolean).join(', ') || '—'}</Cell>
                  <Cell><Badge tone={TONE[o.verification_status]}>{STATUS[o.verification_status]}</Badge></Cell>
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