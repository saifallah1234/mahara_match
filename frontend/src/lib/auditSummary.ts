// Placement: frontend/src/lib/auditSummary.ts
import type { AdminOrganization, AdminUser, AuditLog } from '../api/admin.ts'
import { AUDIT_ACTOR_LABEL, AUDIT_ENTITY_LABEL, labelFor } from './format.ts'

type Person = Pick<AdminUser, 'id' | 'first_name' | 'last_name'>
type Org = Pick<AdminOrganization, 'id' | 'legal_name'>
type Log = Pick<AuditLog, 'actor_user_id' | 'actor_type' | 'entity_type' | 'entity_id'>

/** Who did the operation and which record it concerns, from the lists the admin page already reads. */
export function auditSummary(log: Log, users: Person[], organizations: Org[]): { actor: string; record: string } {
  const person = (id: string | null) => {
    const user = users.find((u) => u.id === id)
    return user && `${user.first_name} ${user.last_name}`
  }
  const kind = labelFor(AUDIT_ENTITY_LABEL, log.entity_type, 'Autre entité')
  const name = log.entity_type === 'user' ? person(log.entity_id)
    : log.entity_type === 'organization' ? organizations.find((o) => o.id === log.entity_id)?.legal_name
    : undefined
  return {
    actor: person(log.actor_user_id) ?? labelFor(AUDIT_ACTOR_LABEL, log.actor_type, 'Système'),
    record: name ? `${kind} « ${name} »` : kind,
  }
}
