import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, EmptyState, Loading, Panel, Row, Select, Table } from '../../components/ui'
import { useAuditLogs } from '../../state/adminData'
import { useAdmin } from '../../state/admin'
import { AUDIT_ACTION_LABEL, AUDIT_ACTOR_LABEL, AUDIT_ENTITY_LABEL, formatDateTime, labelFor } from '../../lib/format'

export default function AdminAudit() {
  const { data: logs, loading, error, hasMore, loadMore } = useAuditLogs()
  const { users } = useAdmin()
  const [kind, setKind] = useState('')
  const kinds = [...new Set(logs.map((l) => l.actor_type))]
  const shown = logs.filter((l) => !kind || l.actor_type === kind)
  const actorName = (id: string | null) => {
    const user = users.find((u) => u.id === id)
    return user ? `${user.first_name} ${user.last_name}` : 'Utilisateur inconnu'
  }
  return (
    <>
      <PageHeader
        title="Journal d’audit"
        action={
          <Select value={kind} onChange={(e) => setKind(e.target.value)} className="min-w-48">
            <option value="">Tous les auteurs</option>
            {kinds.map((k) => <option key={k} value={k}>{labelFor(AUDIT_ACTOR_LABEL, k)}</option>)}
          </Select>
        }
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <Panel>
          {loading ? <Loading /> : shown.length === 0 ? (
            <EmptyState title="Aucune entrée dans le journal.">Les opérations des comptes et du système apparaîtront ici.</EmptyState>
          ) : (
            <Table head={['Horodatage', 'Auteur', 'Action', 'Entité', 'Adresse IP']}>
              {shown.map((l) => (
                <Row key={l.id}>
                  <Cell className="whitespace-nowrap text-[13px] text-slate">{formatDateTime(l.created_at)}</Cell>
                  <Cell>
                    <Badge tone={l.actor_type.toUpperCase().includes('AGENT') ? 'teal' : 'neutre'}>{labelFor(AUDIT_ACTOR_LABEL, l.actor_type)}</Badge>
                    {l.actor_user_id && <p className="text-[12px] text-slate">{actorName(l.actor_user_id)}</p>}
                  </Cell>
                  <Cell className="text-[13px] text-navy">{labelFor(AUDIT_ACTION_LABEL, l.action, 'Autre action')}</Cell>
                  <Cell className="text-[13px] text-slate">{labelFor(AUDIT_ENTITY_LABEL, l.entity_type, 'Autre entité')}</Cell>
                  <Cell className="tnum text-[13px] text-slate">{l.ip_address ?? '—'}</Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
        {hasMore && <div className="mt-4 text-center"><Button variant="secondaire" disabled={loading} onClick={() => void loadMore()}>Charger plus</Button></div>}
      </PageBody>
    </>
  )
}