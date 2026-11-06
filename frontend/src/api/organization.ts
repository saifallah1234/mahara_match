// Placement: frontend/src/api/organization.ts
import { allPages } from './auth.ts'
import { request } from './client.ts'

export type OrganizationMember = {
  id: string; user: string; first_name: string; last_name: string; email: string
  role: string | null; job_title: string; joined_at: string | null
}

export const listMembers = (organizationId: string) => allPages<OrganizationMember>(`/organizations/${organizationId}/members/`)
export const addMember = (organizationId: string, body: { user: string; job_title: string; joined_at: string | null }) =>
  request<OrganizationMember>(`/organizations/${organizationId}/members/`, { method: 'POST', body: JSON.stringify(body) })
export const updateMember = (organizationId: string, userId: string, body: { job_title: string; joined_at: string | null }) =>
  request<OrganizationMember>(`/organizations/${organizationId}/members/${userId}/`, { method: 'PATCH', body: JSON.stringify(body) })
export const removeMember = (organizationId: string, userId: string) =>
  request<void>(`/organizations/${organizationId}/members/${userId}/`, { method: 'DELETE' })
