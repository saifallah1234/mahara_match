import { apiErrorMessage } from '../lib/format.ts'

export const API_BASE_URL = '/api/v1'

let accessToken: string | null = null
let refreshInFlight: Promise<string> | null = null
let onSessionExpired: (() => void) | null = null

export function setAccessToken(token: string | null) { accessToken = token }
export function getAccessToken() { return accessToken }
export function setSessionExpiredHandler(handler: (() => void) | null) { onSessionExpired = handler }

function csrfToken(): string {
  const cookie = document.cookie.split('; ').find((part) => part.startsWith('csrftoken='))
  return cookie ? decodeURIComponent(cookie.slice('csrftoken='.length)) : ''
}

export async function ensureCsrf(): Promise<void> {
  if (csrfToken()) return
  const response = await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: 'same-origin' })
  if (!response.ok) throw await responseError(response)
}

async function responseError(response: Response): Promise<ApiError> {
  const payload = await response.json().catch(() => ({}))
  const error = payload.error ?? {}
  const code = error.code ?? 'request_error'
  return new ApiError(response.status, code, apiErrorMessage(code, error.message ?? response.statusText, error.details), error.details)
}

async function send<T>(path: string, init: RequestInit = {}, token = accessToken): Promise<T> {
  const headers = new Headers(init.headers)
  if (init.body && !(init.body instanceof FormData)) headers.set('Content-Type', 'application/json')
  if (token) headers.set('Authorization', `Bearer ${token}`)
  if (init.method && !['GET', 'HEAD'].includes(init.method.toUpperCase())) {
    const csrf = csrfToken()
    if (csrf) headers.set('X-CSRFToken', csrf)
  }
  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, credentials: 'same-origin', headers })
  if (!response.ok) throw await responseError(response)
  return response.status === 204 ? undefined as T : response.json() as Promise<T>
}

export async function authPost<T>(path: string, body?: object, token = accessToken): Promise<T> {
  await ensureCsrf()
  return send<T>(path, { method: 'POST', body: body ? JSON.stringify(body) : undefined }, token)
}

export async function refreshAccess(): Promise<string> {
  if (!refreshInFlight) {
    refreshInFlight = authPost<{ access: string }>('/auth/token/refresh/', undefined, null)
      .then(({ access }) => { setAccessToken(access); return access })
      .finally(() => { refreshInFlight = null })
  }
  return refreshInFlight
}

/** Same-origin API transport with one refresh-and-retry on expired access. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  try {
    return await send<T>(path, init)
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error
    try {
      const token = await refreshAccess()
      return await send<T>(path, init, token)
    } catch (retryError) {
      if (retryError instanceof ApiError && retryError.status === 401) {
        setAccessToken(null)
        onSessionExpired?.()
      }
      throw retryError
    }
  }
}

export async function requestBlob(path: string): Promise<Blob> {
  const download = (token: string | null) => fetch(`${API_BASE_URL}${path}`, {
    credentials: 'same-origin', headers: token ? { Authorization: `Bearer ${token}` } : {},
  })
  let response = await download(accessToken)
  if (response.status === 401) {
    try { response = await download(await refreshAccess()) }
    catch (error) {
      if (error instanceof ApiError && error.status === 401) { setAccessToken(null); onSessionExpired?.() }
      throw error
    }
    if (response.status === 401) { setAccessToken(null); onSessionExpired?.() }
  }
  if (!response.ok) throw await responseError(response)
  return response.blob()
}

export class ApiError extends Error {
  status: number
  code: string
  details?: unknown
  constructor(
    status: number,
    code: string,
    message: string,
    details?: unknown,
  ) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

