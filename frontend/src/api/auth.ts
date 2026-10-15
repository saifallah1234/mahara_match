import { ApiError, authPost, getAccessToken, refreshAccess, request, setAccessToken } from './client.ts'
import type { RoleCode, UserStatus } from '../lib/types'

export interface Workspace {
  role_code: RoleCode
  organization: null | { id: string; legal_name: string; type: string; verification_status: string }
}

export interface CurrentUser {
  id: string
  email: string
  first_name: string
  last_name: string
  phone?: string
  status: UserStatus
  role_assignments: Array<{ role_code: RoleCode; organization_id: string | null }>
  workspaces: Workspace[]
}

export interface Registration {
  email: string
  password: string
  first_name: string
  last_name: string
  phone?: string
  account_type: 'CANDIDATE' | 'RECRUITER' | 'TRAINING_MANAGER'
  organization_name?: string
  matricule_fiscal?: string
}

export async function login(email: string, password: string): Promise<CurrentUser> {
  const { access } = await authPost<{ access: string }>('/auth/token/', { email, password }, null)
  setAccessToken(access)
  return me()
}

export async function restore(): Promise<CurrentUser> {
  await refreshAccess()
  return me()
}

export function me(): Promise<CurrentUser> { return request('/users/me/') }
export async function allPages<T>(path: string): Promise<T[]> {
  const items: T[] = []
  for (let page = 1; ; page++) {
    const result = await request<{ results: T[]; next: string | null }>(`${path}${path.includes('?') ? '&' : '?'}page=${page}&page_size=100`)
    items.push(...result.results)
    if (!result.next) return items
  }
}
export function register(data: Registration): Promise<{ user_id: string; status: string }> {
  return authPost('/auth/register/', data, null)
}

export async function logout(): Promise<void> {
  if (!getAccessToken()) await refreshAccess()
  try { await authPost<void>('/auth/logout/') }
  catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error
    await refreshAccess()
    await authPost<void>('/auth/logout/')
  } finally { setAccessToken(null) }
}
