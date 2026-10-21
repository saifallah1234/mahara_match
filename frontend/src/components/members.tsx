// Placement: frontend/src/components/members.tsx
import { useEffect, useState, type ReactNode } from 'react'
import { Cell, EmptyState, Panel, Row, Table } from './ui'
import { listMembers, type OrganizationMember } from '../api/organization'
import { ROLE_LABEL, formatDate, labelFor } from '../lib/format'

/**
 * Liste des membres. Lecture seule par défaut ; l’admin passe `action` (en-tête) et `rowAction` (par ligne).
 * `refreshKey` : changer sa valeur recharge la liste après une modification.
 */
export function MembersPanel({
  organizationId,
  action,
  rowAction,
  refreshKey = 0,
}: {
  organizationId: string
  action?: ReactNode
  rowAction?: (member: OrganizationMember) => ReactNode
  refreshKey?: number
}) {
  const [members, setMembers] = useState<OrganizationMember[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let live = true
    setLoading(true); setError(null)
    listMembers(organizationId)
      .then((rows) => { if (live) setMembers(rows) })
      .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Chargement impossible.') })
      .finally(() => { if (live) setLoading(false) })
    return () => { live = false }
  }, [organizationId, refreshKey])

  const head = ['Nom', 'E-mail', 'Rôle', 'Membre depuis', ...(rowAction ? [''] : [])]
  return (
    <Panel title="Membres de l’organisation" action={action}>
      {error && <p role="alert" className="px-5 py-4 text-coral">{error}</p>}
      {loading ? <p className="p-5 text-slate">Chargement…</p> : members.length === 0 ? (
        <EmptyState title="Aucun membre" />
      ) : (
        <Table head={head}>
          {members.map((member) => (
            <Row key={member.id}>
              <Cell className="font-medium text-navy">{member.first_name} {member.last_name}</Cell>
              <Cell className="text-[13px]">{member.email}</Cell>
              <Cell className="text-[13px]">{member.role ? labelFor(ROLE_LABEL, member.role, 'Autre rôle') : '—'}</Cell>
              <Cell className="text-[13px]">{member.joined_at ? formatDate(member.joined_at) : '—'}</Cell>
              {rowAction && <Cell className="text-right">{rowAction(member)}</Cell>}
            </Row>
          ))}
        </Table>
      )}
    </Panel>
  )
}
