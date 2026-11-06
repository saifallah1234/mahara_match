// Placement: frontend/src/lib/citations.ts
import type { RoleCode } from './types'

/** Page for a source citation, or null when the reference has no page in this app. */
export function citationPath(reference: string, role: RoleCode): string | null {
  const [kind, id] = reference.split(':')
  if (!id) return null
  if (kind === 'candidate_profile') return `/recruteur/candidats/${id}`
  if (kind === 'offer') return role === 'RECRUITER' ? `/recruteur/offres/${id}` : `/candidat/offres/${id}`
  return null
}
