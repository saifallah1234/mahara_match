import { useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, ConfirmDialog, EmptyState, Input, Panel, Row, Select, Table } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import { ROLE_LABEL, formatDate, labelFor } from '../../lib/format'
import { filterUsers } from '../../lib/adminFilters'
import { AccountDetailDialog, CreateAccountDialog } from './AccountDialogs'

const STATUS = { PENDING: 'En attente', ACTIVE: 'Actif', SUSPENDED: 'Suspendu', DISABLED: 'Désactivé' } as const
const TONE = { PENDING: 'attention', ACTIVE: 'positif', SUSPENDED: 'negatif', DISABLED: 'neutre' } as const

export default function AdminComptes() {
  const { users, organizations, loading, error, setUserStatus } = useAdmin()
  const [q, setQ] = useState('')
  const [role, setRole] = useState('')
  const [creating, setCreating] = useState(false)
  const [detail, setDetail] = useState<string | null>(null)
  const shown = filterUsers(users, { q, role })
  const orgNames = (u: (typeof users)[number]) => {
    const names = u.role_assignments
      .map((r) => organizations.find((o) => o.id === r.organization_id)?.legal_name)
      .filter((name): name is string => Boolean(name))
    return [...new Set(names)].join(', ') || '—'
  }
  const change = (id: string, s: 'ACTIVE' | 'SUSPENDED') => void setUserStatus(id, s).catch(() => {})
  const [suspending, setSuspending] = useState<(typeof users)[number] | null>(null)

  return (
    <>
      <PageHeader
        title="Comptes et rôles"
        action={
          <div className="flex flex-wrap gap-2">
            <Input placeholder="Nom ou e-mail…" value={q} onChange={(e) => setQ(e.target.value)} className="min-w-56" />
            <Select value={role} onChange={(e) => setRole(e.target.value)} className="min-w-56">
              <option value="">Tous les rôles</option>
              {Object.entries(ROLE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
            </Select>
            <Button onClick={() => setCreating(true)}>Créer un compte</Button>
          </div>
        }
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : shown.length === 0 ? (
            <EmptyState title="Aucun compte ne correspond." />
          ) : (
            <Table head={['Utilisateur', 'Rôles', 'Organisation', 'Dernière connexion', 'Statut', '']}>
              {shown.map((u) => (
                <Row key={u.id}>
                  <Cell><p className="font-medium text-navy">{u.first_name} {u.last_name}</p><p className="text-[12.5px] text-slate">{u.email}</p></Cell>
                  <Cell className="text-[13px]">{u.role_assignments.map((r) => labelFor(ROLE_LABEL, r.role_code, 'Autre rôle')).join(', ') || '—'}</Cell>
                  <Cell className="text-[13px] text-slate">{orgNames(u)}</Cell>
                  <Cell className="text-[13px] text-slate">{u.last_login ? formatDate(u.last_login) : 'Jamais'}</Cell>
                  <Cell><Badge tone={TONE[u.status]}>{STATUS[u.status]}</Badge></Cell>
                  <Cell className="text-right">
                    <Button size="sm" variant="discret" onClick={() => setDetail(u.id)}>Détails</Button>{' '}
                    {u.status === 'PENDING' && <Link to="/admin/demandes" className="text-[13px] font-medium text-teal hover:underline">Demande d’accès</Link>}
                    {u.status === 'ACTIVE' && <Button size="sm" variant="discret" onClick={() => setSuspending(u)}>Suspendre</Button>}
                    {(u.status === 'SUSPENDED' || u.status === 'DISABLED') && <Button size="sm" onClick={() => change(u.id, 'ACTIVE')}>Réactiver</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
        {creating && <CreateAccountDialog onClose={() => setCreating(false)} />}
        {detail && <AccountDetailDialog userId={detail} onClose={() => setDetail(null)} />}
        {suspending && (
          <ConfirmDialog
            title="Suspendre ce compte ?"
            danger
            onCancel={() => setSuspending(null)}
            onConfirm={() => { change(suspending.id, 'SUSPENDED'); setSuspending(null) }}
          >
            Le compte de {suspending.first_name} {suspending.last_name} sera suspendu. Il pourra être réactivé à tout moment.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}
