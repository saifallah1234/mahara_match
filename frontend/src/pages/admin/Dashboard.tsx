import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { EmptyState, Loading, Panel, StatTile } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import { useAuditLogs, useBatches } from '../../state/adminData'
import { AUDIT_ACTION_LABEL, formatDateTime, labelFor } from '../../lib/format'
import { auditSummary } from '../../lib/auditSummary'

export default function AdminDashboard() {
  const { users, organizations, error } = useAdmin()
  const batchCount = useBatches().count
  const { data: audit, loading: auditLoading } = useAuditLogs()
  return (
    <>
      <PageHeader title="Administration" />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={users.length} label="Comptes" note={`${users.filter((u) => u.status === 'ACTIVE').length} actifs`} />
          <StatTile value={users.filter((u) => u.status === 'PENDING').length} label="Comptes en attente" tone="coral" />
          <StatTile value={organizations.filter((o) => o.verification_status === 'PENDING').length} label="Organisations à vérifier" tone="teal" />
          <StatTile value={batchCount} label="Lots d’import" tone="leaf" />
        </div>
        <Panel title="Dernières opérations" action={<Link to="/admin/audit" className="text-[13px] font-medium text-teal hover:underline">Journal complet</Link>}>
          {auditLoading && audit.length === 0 ? <Loading /> : audit.length === 0 ? <EmptyState title="Aucune opération pour le moment.">Les créations, vérifications et imports apparaîtront ici.</EmptyState> : (
            <ul className="divide-y divide-line/70">
              {audit.slice(0, 6).map((l) => {
                const { actor, record } = auditSummary(l, users, organizations)
                return (
                  <li key={l.id} className="flex flex-wrap justify-between gap-x-3 gap-y-0.5 px-5 py-3 text-[13.5px]">
                    <span className="text-navy"><span className="font-medium">{actor}</span> · {labelFor(AUDIT_ACTION_LABEL, l.action, 'Autre action')} · {record}</span>
                    <span className="text-slate">{formatDateTime(l.created_at)}</span>
                  </li>
                )
              })}
            </ul>
          )}
        </Panel>
      </PageBody>
    </>
  )
}