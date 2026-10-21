// Placement: frontend/src/lib/adminFilters.ts

export const ADMIN_CREATABLE_ROLES = ['RECRUITER', 'TRAINING_MANAGER', 'MINISTRY_MANAGER', 'ADMIN']

export const ORGANIZATION_TYPE_LABEL: Record<string, string> = {
  COMPANY: 'Entreprise', SUBSIDIARY: 'Filiale', TRAINING_PROVIDER: 'Organisme de formation', ANETI: 'ANETI', MINISTRY: 'Ministère',
}
export const ORGANIZATION_STATUS_LABEL: Record<string, string> = { PENDING: 'En attente', VERIFIED: 'Vérifiée', REJECTED: 'Rejetée' }

/** Organisations acceptées par rôle (identity/services/contracts.py). Les autres rôles sont globaux. */
const ROLE_ORGANIZATION_TYPES: Record<string, string[]> = {
  RECRUITER: ['COMPANY', 'SUBSIDIARY'], TRAINING_MANAGER: ['TRAINING_PROVIDER'], MINISTRY_MANAGER: ['MINISTRY'],
}

export function roleNeedsOrganization(role: string): boolean {
  return role in ROLE_ORGANIZATION_TYPES
}

/** Organisations où attribuer ce rôle : du bon type et vérifiées, seules les vérifiées donnent des permissions. */
export function organizationsForRole<T extends { type: string; verification_status: string }>(orgs: T[], role: string): T[] {
  const types = ROLE_ORGANIZATION_TYPES[role] ?? []
  return orgs.filter((o) => types.includes(o.type) && o.verification_status === 'VERIFIED')
}

type Assigned = { first_name: string; last_name: string; email: string; role_assignments: { role_code: string }[] }

export function filterUsers<T extends Assigned>(users: T[], { q, role }: { q: string; role: string }): T[] {
  const needle = q.trim().toLowerCase()
  return users.filter((u) => {
    if (role && !u.role_assignments.some((r) => r.role_code === role)) return false
    if (!needle) return true
    return `${u.first_name} ${u.last_name} ${u.email}`.toLowerCase().includes(needle)
  })
}

export function filterOrganizations<T extends { type: string; verification_status: string }>(orgs: T[], { status, type }: { status: string; type: string }): T[] {
  return orgs.filter((o) => (!status || o.verification_status === status) && (!type || o.type === type))
}
