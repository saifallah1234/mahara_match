import { allPages } from './auth.ts'
import { request } from './client.ts'

export type AdminUser = {
  id: string; email: string; first_name: string; last_name: string; status: 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'DISABLED'
  last_login: string | null; role_assignments: { role_code: string; organization_id: string | null }[]
}
export type AdminOrganization = {
  id: string; type: string; legal_name: string; matricule_fiscal: string; governorate: string; city: string
  address_line: string; verification_status: 'PENDING' | 'VERIFIED' | 'REJECTED'
}
export type AdminRole = { id: string; code: string; name: string }
export type UserRole = { id: string; user_id: string; role_id: string; role_code: string; organization_id: string | null }
export type Paged<T> = { items: T[]; count: number; hasMore: boolean }
type PageResponse<T> = { results: T[]; count: number; next: string | null }

const PAGE_SIZE = 50
const post = <T>(path: string, body?: object) => request<T>(path, { method: 'POST', body: JSON.stringify(body ?? {}) })
const patch = <T>(path: string, body: object) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) })
const del = (path: string) => request<void>(path, { method: 'DELETE' })

/** Une page d'une liste paginée par DRF, pour le bouton « Charger plus ». */
async function pageOf<T>(path: string, page: number, params: Record<string, string> = {}): Promise<Paged<T>> {
  const query = new URLSearchParams({ ...params, page: String(page), page_size: String(PAGE_SIZE) })
  const result = await request<PageResponse<T>>(`${path}?${query}`)
  return { items: result.results, count: result.count, hasMore: result.next !== null }
}

export const listUsers = () => allPages<AdminUser>('/users/')
export const createUser = (body: { email: string; password: string; first_name: string; last_name: string }) => post<AdminUser>('/users/', body)
export const setUserStatus = (id: string, status: AdminUser['status']) => post<AdminUser>(`/users/${id}/status/`, { status })
export const listRoles = () => allPages<AdminRole>('/roles/')
export const listUserRoles = () => allPages<UserRole>('/user-roles/')
export const assignRole = (body: { user_id: string; role_id: string; organization_id: string | null }) => post<UserRole>('/user-roles/', body)
export const removeRole = (id: string) => del(`/user-roles/${id}/`)

export const listOrganizations = () => allPages<AdminOrganization>('/organizations/')
export const updateOrganization = (id: string, body: Partial<Pick<AdminOrganization, 'legal_name' | 'matricule_fiscal' | 'governorate' | 'city' | 'address_line'>>) =>
  patch<AdminOrganization>(`/organizations/${id}/`, body)
export const verifyOrganization = (id: string) => post<AdminOrganization>(`/organizations/${id}/verify/`)
export const rejectOrganization = (id: string) => post<AdminOrganization>(`/organizations/${id}/reject/`)

export type AuditLog = {
  id: string; actor_user_id: string | null; actor_type: string; action: string
  entity_type: string; entity_id: string | null; ip_address: string | null; created_at: string
}
export type DataSource = {
  id: string; name: string; type: 'API' | 'CSV' | 'MANUAL_FILE'; base_url: string | null; configuration_json: unknown
  is_authorized: boolean; acquisition_method: string | null; expires_at: string | null
}
export type ImportBatch = {
  id: string; source_id: string; status: string; started_at: string | null; completed_at: string | null
  added_count: number; updated_count: number; unchanged_count: number; rejected_count: number; created_at: string
}
export type ImportRow = {
  id: string; batch_id: string; row_number: number; external_id: string; payload_json: unknown
  status: 'ADDED' | 'UPDATED' | 'UNCHANGED' | 'REJECTED'; error_code: string; error_message: string
  job_offer_id: string | null
}

export const listAuditPage = (page: number) => pageOf<AuditLog>('/audit-logs/', page)
export const listSources = () => allPages<DataSource>('/data-sources/')
export const createSource = (body: object) => post<DataSource>('/data-sources/', body)
export const updateSource = (id: string, body: object) => patch<DataSource>(`/data-sources/${id}/`, body)
export const listBatchPage = (page: number) => pageOf<ImportBatch>('/import-batches/', page)
export const getBatch = (id: string) => request<ImportBatch>(`/import-batches/${id}/`)
export const listBatchRowPage = (batchId: string, status: string, page: number) =>
  pageOf<ImportRow>(`/import-batches/${batchId}/rows/`, page, status ? { status } : {})
export const authorizeSource = (id: string, body: { acquisition_method: string; permission_evidence: string; expires_at: string }) =>
  post<DataSource>(`/data-sources/${id}/authorize/`, body)
export const revokeSource = (id: string) => post<DataSource>(`/data-sources/${id}/revoke/`)
