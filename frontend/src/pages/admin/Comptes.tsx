import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, Panel, Row, Select, Table } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import { formatDate } from '../../lib/format'

const ROLES: Record<string, string> = {
  CANDIDATE: 'Candidat', RECRUITER: 'Recruteur', TRAINING_MANAGER: 'Responsable de formation',
  ANETI_AGENT: 'Agent ANETI', MINISTRY_MANAGER: 'Ministère', ADMIN: 'Administrateur',
}
const STATUS = { PENDING: 'En attente', ACTIVE: 'Actif', SUSPENDED: 'Suspendu', DISABLED: 'Désactivé' } as const
const TONE = { PENDING: 'attention', ACTIVE: 'positif', SUSPENDED: 'negatif', DISABLED: 'neutre' } as const

export default function AdminComptes() {
  const { users, organizations, loading, error, setUserStatus } = useAdmin()
  const [role, setRole] = useState('')
  const shown = users.filter((u) => !role || u.role_assignments.some((r) => r.role_code === role))
  const orgName = (u: (typeof users)[number]) => {
    const id = u.role_assignments.find((r) => r.organization_id)?.organization_id
    return organizations.find((o) => o.id === id)?.legal_name ?? '—'
  }
  const change = (id: string, s: 'ACTIVE' | 'SUSPENDED') => void setUserStatus(id, s).catch(() => {})

  return (
    <>
      <PageHeader
        title="Comptes et rôles"
        action={
          <Select value={role} onChange={(e) => setRole(e.target.value)} className="min-w-56">
            <option value="">Tous les rôles</option>
            {Object.entries(ROLES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        }
      />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        <Panel>
          {loading ? <p className="p-5 text-slate">Chargement…</p> : (
            <Table head={['Utilisateur', 'Rôles', 'Organisation', 'Dernière connexion', 'Statut', '']}>
              {shown.map((u) => (
                <Row key={u.id}>
                  <Cell><p className="font-medium text-navy">{u.first_name} {u.last_name}</p><p className="text-[12.5px] text-slate">{u.email}</p></Cell>
                  <Cell className="text-[13px]">{u.role_assignments.map((r) => ROLES[r.role_code] ?? r.role_code).join(', ') || '—'}</Cell>
                  <Cell className="text-[13px] text-slate">{orgName(u)}</Cell>
                  <Cell className="text-[13px] text-slate">{u.last_login ? formatDate(u.last_login) : 'Jamais'}</Cell>
                  <Cell><Badge tone={TONE[u.status]}>{STATUS[u.status]}</Badge></Cell>
                  <Cell className="text-right">
                    {u.status === 'ACTIVE' && <Button size="sm" variant="discret" onClick={() => change(u.id, 'SUSPENDED')}>Suspendre</Button>}
                    {u.status === 'SUSPENDED' && <Button size="sm" onClick={() => change(u.id, 'ACTIVE')}>Réactiver</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
      </PageBody>
    </>
  )
}