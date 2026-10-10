import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Cell, Panel, Row, Select, Table } from '../../components/ui'
import { useAuditLogs } from '../../state/adminData'
import { formatDateTime } from '../../lib/format'

export default function AdminAudit() {
  const { data: logs, loading, error } = useAuditLogs()
  const [kind, setKind] = useState('')
  const kinds = [...new Set(logs.map((l) => l.actor_type))]
  const shown = logs.filter((l) => !kind || l.actor_type === kind)
  return (
    <>
      <PageHeader
        title="Journal d’audit"
        action={
          <Select value={kind} onChange={(e) => setKind(e.target.value)} className="min-w-48">
            <option value="">Tous les auteurs</option>
            {kinds.map((k) => <option key={k} value={k}>{k}</option>)}
          </Select>
        }
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : shown.length === 0 ? (
            <p className="p-5 text-[13.5px] text-slate">Aucune entrée dans le journal.</p>
          ) : (
            <Table head={['Horodatage', 'Auteur', 'Action', 'Entité', 'Adresse IP']}>
              {shown.map((l) => (
                <Row key={l.id}>
                  <Cell className="whitespace-nowrap text-[13px] text-slate">{formatDateTime(l.created_at)}</Cell>
                  <Cell>
                    <Badge tone={l.actor_type.toUpperCase().includes('AGENT') ? 'teal' : 'neutre'}>{l.actor_type}</Badge>
                    {l.actor_user_id && <p className="text-[12px] text-slate">{l.actor_user_id.slice(0, 8)}</p>}
                  </Cell>
                  <Cell className="text-[13px] text-navy">{l.action}</Cell>
                  <Cell className="text-[13px] text-slate">{l.entity_type} <span className="text-slate/70">{l.entity_id?.slice(0, 8)}</span></Cell>
                  <Cell className="tnum text-[13px] text-slate">{l.ip_address ?? '—'}</Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
      </PageBody>
    </>
  )
}