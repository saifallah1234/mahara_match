import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Panel, StatTile } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import { useAuditLogs, useBatches } from '../../state/adminData'
import { formatDateTime } from '../../lib/format'

export default function AdminDashboard() {
  const { users, organizations, error } = useAdmin()
  const batches = useBatches().data
  const audit = useAuditLogs().data
  return (
    <>
      <PageHeader title="Administration" />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={users.length} label="Comptes" note={`${users.filter((u) => u.status === 'ACTIVE').length} actifs`} />
          <StatTile value={users.filter((u) => u.status === 'PENDING').length} label="Comptes en attente" tone="coral" />
          <StatTile value={organizations.filter((o) => o.verification_status === 'PENDING').length} label="Organisations à vérifier" tone="teal" />
          <StatTile value={batches.length} label="Lots d’import" tone="leaf" />
        </div>
        <Panel title="Dernières opérations" action={<Link to="/admin/audit" className="text-[13px] font-medium text-teal hover:underline">Journal complet</Link>}>
          {audit.length === 0 ? <p className="p-5 text-[13.5px] text-slate">Aucune entrée.</p> : (
            <ul className="divide-y divide-line/70">
              {audit.slice(0, 6).map((l) => (
                <li key={l.id} className="flex justify-between gap-3 px-5 py-3 text-[13.5px]">
                  <span className="text-navy">{l.action} · {l.entity_type}</span>
                  <span className="text-slate">{formatDateTime(l.created_at)}</span>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </PageBody>
    </>
  )
}