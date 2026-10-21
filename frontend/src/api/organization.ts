// Placement: frontend/src/api/organization.ts
import { allPages } from './auth.ts'

export type OrganizationMember = {
  id: string; user: string; first_name: string; last_name: string; email: string
  role: string | null; job_title: string; joined_at: string | null
}

export const listMembers = (organizationId: string) => allPages<OrganizationMember>(`/organizations/${organizationId}/members/`)
