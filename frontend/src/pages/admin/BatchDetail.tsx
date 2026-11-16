// Placement: frontend/src/pages/admin/BatchDetail.tsx
import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, EmptyState, Loading, Panel, Row, Select, Table } from '../../components/ui'
import { useBatchRows } from '../../state/adminData'
import * as api from '../../api/admin'
import { IMPORT_BATCH_STATUS_LABEL, IMPORT_REJECTION_LABEL, IMPORT_ROW_STATUS_LABEL, formatDateTime, labelFor } from '../../lib/format'

export default function AdminBatchDetail() {
  const { id = '' } = useParams()
  const [batch, setBatch] = useState<api.ImportBatch | null>(null)
  const [batchError, setBatchError] = useState<string | null>(null)
  const [status, setStatus] = useState('')
  const rows = useBatchRows(id, status)

  useEffect(() => {
    let live = true
    api.getBatch(id)
      .then((b) => { if (live) setBatch(b) })
      .catch((e) => { if (live) setBatchError(e instanceof Error ? e.message : 'Lot introuvable.') })
    return () => { live = false }
  }, [id])

  return (
    <>
      <PageHeader
        title="Détail du lot d’import"
        description={<Link to="/admin/imports" className="text-teal hover:underline">Retour aux imports</Link>}
        action={
          <Select value={status} onChange={(e) => setStatus(e.target.value)} className="min-w-52" aria-label="Statut de la ligne">
            <option value="">Toutes les lignes</option>
            {Object.entries(IMPORT_ROW_STATUS_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        }
      />
      <PageBody className="space-y-6">
        {batchError && <p role="alert" className="text-coral">{batchError}</p>}
        {batch && (
          <p className="text-[13.5px] text-slate">
            {formatDateTime(batch.started_at ?? batch.created_at)} · <Badge tone={batch.status === 'COMPLETED' ? 'positif' : 'neutre'}>{labelFor(IMPORT_BATCH_STATUS_LABEL, batch.status)}</Badge>
            {' '}· {batch.added_count} ajoutée(s), {batch.updated_count} mise(s) à jour, {batch.unchanged_count} inchangée(s), {batch.rejected_count} rejetée(s)
          </p>
        )}
        {rows.error && <p role="alert" className="text-coral">{rows.error}</p>}
        <Panel>
          {rows.loading && rows.data.length === 0 ? <Loading /> : rows.data.length === 0 ? (
            <EmptyState title="Aucune ligne pour ce filtre.">Choisissez un autre statut.</EmptyState>
          ) : (
            <Table head={['Ligne', 'Statut', 'Identifiant externe', 'Motif', 'Offre', 'Contenu brut']}>
              {rows.data.map((r) => (
                <Row key={r.id}>
                  <Cell className="tnum text-[13px] text-slate">{r.row_number}</Cell>
                  <Cell><Badge tone={r.status === 'REJECTED' ? 'negatif' : 'positif'}>{labelFor(IMPORT_ROW_STATUS_LABEL, r.status)}</Badge></Cell>
                  <Cell className="tnum text-[13px]">{r.external_id || '—'}</Cell>
                  <Cell className="text-[13px] text-navy">{r.status === 'REJECTED' ? labelFor(IMPORT_REJECTION_LABEL, r.error_code, 'Autre motif') : '—'}</Cell>
                  <Cell className="break-all text-[12px] text-slate">{r.job_offer_id ?? '—'}</Cell>
                  <Cell>
                    <details>
                      <summary className="cursor-pointer text-[13px] text-teal">Voir</summary>
                      <pre className="mt-2 max-h-64 overflow-auto rounded-[6px] bg-mist p-3 text-[12px] text-navy">{JSON.stringify(r.payload_json, null, 2)}</pre>
                    </details>
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
        {rows.hasMore && <div className="text-center"><Button variant="secondaire" disabled={rows.loading} onClick={() => void rows.loadMore()}>Charger plus</Button></div>}
      </PageBody>
    </>
  )
}
