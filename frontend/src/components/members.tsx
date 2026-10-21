// Placement: frontend/src/components/members.tsx
import { useEffect, useState } from 'react'
import { Cell, EmptyState, Panel, Row, Table } from './ui'
import { listMembers, type OrganizationMember } from '../api/organization'
import { formatDate } from '../lib/format'

const ROLE_LABEL: Record<string, string> = { RECRUITER: 'Recruteur', TRAINING_MANAGER: 'Gestionnaire de formation' }

/** Lecture seule : les membres voient qui partage leur organisation, sans pouvoir le modifier. */
export function MembersPanel({ organizationId }: { organizationId: string }) {
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
  }, [organizationId])

  return (
    <Panel title="Membres de l’organisation">
      {error && <p role="alert" className="px-5 py-4 text-coral">{error}</p>}
      {loading ? <p className="p-5 text-slate">Chargement…</p> : members.length === 0 ? (
        <EmptyState title="Aucun membre" />
      ) : (
        <Table head={['Nom', 'E-mail', 'Rôle', 'Membre depuis']}>
          {members.map((member) => (
            <Row key={member.id}>
              <Cell className="font-medium text-navy">{member.first_name} {member.last_name}</Cell>
              <Cell className="text-[13px]">{member.email}</Cell>
              <Cell className="text-[13px]">{member.role ? ROLE_LABEL[member.role] ?? member.role : '—'}</Cell>
              <Cell className="text-[13px]">{member.joined_at ? formatDate(member.joined_at) : '—'}</Cell>
            </Row>
          ))}
        </Table>
      )}
    </Panel>
  )
}
