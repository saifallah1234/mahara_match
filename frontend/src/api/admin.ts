import { allPages } from './auth.ts'
import { request } from './client.ts'

export type AdminUser = {
  id: string; email: string; first_name: string; last_name: string; status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'DISABLED'
  last_login: string | null; role_assignments: { role_code: string; organization_id: string | null }[]
}
export type AdminOrganization = {
  id: string; type: string; legal_name: string; matricule_fiscal: string; governorate: string; city: string
  verification_status: 'PENDING' | 'VERIFIED' | 'REJECTED'
}

const post = <T>(path: string, body?: object) => request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) })

export const listUsers = () => allPages<AdminUser>('/users/')
export const listOrganizations = () => allPages<AdminOrganization>('/organizations/')
export const setUserStatus = (id: string, status: AdminUser['status']) => post<AdminUser>(`/users/${id}/status/`, { status })
export const verifyOrganization = (id: string) => post<AdminOrganization>(`/organizations/${id}/verify/`)
export const rejectOrganization = (id: string) => post<AdminOrganization>(`/organizations/${id}/reject/`)

export type AuditLog = {
  id: string; actor_user_id: string | null; actor_type: string; action: string
  entity_type: string; entity_id: string | null; ip_address: string | null; created_at: string
}
export type DataSource = {
  id: string; name: string; type: 'API' | 'CSV' | 'MANUAL_FILE'; base_url: string | null
  is_authorized: boolean; acquisition_method: string | null; expires_at: string | null
}
export type ImportBatch = {
  id: string; source_id: string; status: string; started_at: string | null; completed_at: string | null
  added_count: number; updated_count: number; unchanged_count: number; rejected_count: number; created_at: string
}
type Page<T> = { results: T[] }

export const listAuditLogs = () => request<Page<AuditLog>>('/audit-logs/?page_size=100').then((r) => r.results)
export const listSources = () => allPages<DataSource>('/data-sources/')
export const listBatches = () => request<Page<ImportBatch>>('/import-batches/?page_size=100').then((r) => r.results)
export const authorizeSource = (id: string, body: { acquisition_method: string; permission_evidence: string; expires_at: string }) =>
  post<DataSource>(`/data-sources/${id}/authorize/`, body)
export const revokeSource = (id: string) => post<DataSource>(`/data-sources/${id}/revoke/`)