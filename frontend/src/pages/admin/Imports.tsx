import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, EmptyState, Field, Input, Panel, Row, Table } from '../../components/ui'
import { useBatches, useSources } from '../../state/adminData'
import * as api from '../../api/admin'
import { formatDateTime } from '../../lib/format'

export default function AdminImports() {
  const sources = useSources()
  const batches = useBatches()
  const [editing, setEditing] = useState<string | null>(null)
  const [form, setForm] = useState({ acquisition_method: '', permission_evidence: '', expires_at: '' })
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })
  const sourceName = (id: string) => sources.data.find((s) => s.id === id)?.name ?? id.slice(0, 8)

  async function run(work: () => Promise<unknown>) {
    setError(null)
    try { await work(); setEditing(null); await sources.reload() }
    catch (e) { setError(e instanceof Error ? e.message : 'Opération refusée.') }
  }

  return (
    <>
      <PageHeader title="Imports d’offres" />
      <PageBody className="space-y-6">
        {(error || sources.error || batches.error) && <p role="alert" className="text-coral">{error ?? sources.error ?? batches.error}</p>}
        <Panel title="Sources de données">
          {sources.loading ? <p className="p-5 text-slate">Chargement…</p> : sources.data.length === 0 ? (
            <EmptyState title="Aucune source déclarée" />
          ) : (
            <Table head={['Source', 'Type', 'Autorisation', '']}>
              {sources.data.map((s) => (
                <Row key={s.id}>
                  <Cell><span className="font-medium text-navy">{s.name}</span>{s.base_url && <p className="text-[12.5px] text-slate">{s.base_url}</p>}</Cell>
                  <Cell className="text-[13px]">{s.type}</Cell>
                  <Cell>
                    <Badge tone={s.is_authorized ? 'positif' : 'attention'}>{s.is_authorized ? 'Autorisée' : 'Non autorisée'}</Badge>
                    {s.expires_at && <p className="text-[12px] text-slate">jusqu’au {formatDateTime(s.expires_at)}</p>}
                  </Cell>
                  <Cell className="text-right">
                    {s.is_authorized
                      ? <Button size="sm" variant="discret" onClick={() => void run(() => api.revokeSource(s.id))}>Révoquer</Button>
                      : <Button size="sm" onClick={() => setEditing(editing === s.id ? null : s.id)}>Autoriser</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
          {editing && (
            <div className="grid gap-4 border-t border-line p-5 sm:grid-cols-2">
              <Field label="Mode d’acquisition" required><Input value={form.acquisition_method} onChange={set('acquisition_method')} placeholder="Convention, API ouverte…" /></Field>
              <Field label="Valable jusqu’au" required><Input type="datetime-local" value={form.expires_at} onChange={set('expires_at')} /></Field>
              <div className="sm:col-span-2"><Field label="Preuve de l’autorisation" required><Input value={form.permission_evidence} onChange={set('permission_evidence')} /></Field></div>
              <div className="sm:col-span-2">
                <Button
                  disabled={!form.acquisition_method.trim() || !form.permission_evidence.trim() || !form.expires_at}
                  onClick={() => void run(() => api.authorizeSource(editing, { ...form, expires_at: new Date(form.expires_at).toISOString() }))}
                >
                  Valider l’autorisation
                </Button>
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Lots d’import">
          {batches.loading ? <p className="p-5 text-slate">Chargement…</p> : batches.data.length === 0 ? (
            <EmptyState title="Aucun import réalisé" />
          ) : (
            <Table head={['Source', 'Date', 'Ajoutées', 'Mises à jour', 'Inchangées', 'Rejetées', 'Statut']}>
              {batches.data.map((b) => (
                <Row key={b.id}>
                  <Cell className="text-[13px] text-navy">{sourceName(b.source_id)}</Cell>
                  <Cell className="text-[13px] text-slate">{formatDateTime(b.started_at ?? b.created_at)}</Cell>
                  <Cell className="tnum text-[13px]">{b.added_count}</Cell>
                  <Cell className="tnum text-[13px]">{b.updated_count}</Cell>
                  <Cell className="tnum text-[13px]">{b.unchanged_count}</Cell>
                  <Cell className="tnum text-[13px]">{b.rejected_count}</Cell>
                  <Cell><Badge tone={b.status === 'COMPLETED' ? 'positif' : 'neutre'}>{b.status}</Badge></Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
      </PageBody>
    </>
  )
}