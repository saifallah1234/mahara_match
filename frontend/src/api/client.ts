import type {
  Application,
  ApplicationStatus,
  CandidateProfile,
  JobOffer,
  RoleCode,
  UUID,
} from '../lib/types'
import { canTransition } from '../lib/statusMachine.ts'

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
  return new ApiError(response.status, error.code ?? 'request_error', error.message ?? response.statusText, error.details)
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

/** Latence simulée, pour que les états de chargement soient visibles. */
const LATENCY_MS = 220

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS))
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

/* ------------------------------------------------------------------ */
/* Règles métier appliquées côté service                               */
/* ------------------------------------------------------------------ */

export interface ApplyInput {
  profile: CandidateProfile
  offer: JobOffer
  cvId: UUID
  coverLetter: string
  existing: Application[]
}

export type ApplyOutcome =
  | { ok: true }
  | { ok: false; code: 'OFFER_CLOSED' | 'DEADLINE_PASSED' | 'DUPLICATE' | 'EXTERNAL_ONLY'; message: string }

/**
 * Contrôles exécutés avant tout dépôt, quelle que soit l'interface
 * d'origine (espace candidat ou agent conversationnel).
 */
export function checkApply(input: ApplyInput): ApplyOutcome {
  const { offer, profile, existing } = input

  if (offer.status !== 'PUBLISHED') {
    return { ok: false, code: 'OFFER_CLOSED', message: 'Cette offre n’est plus ouverte. Le dépôt est refusé.' }
  }

  if (offer.applicationDeadline && new Date(offer.applicationDeadline) < new Date()) {
    return { ok: false, code: 'DEADLINE_PASSED', message: 'La date limite de candidature est dépassée.' }
  }

  if (!offer.easyApply) {
    return {
      ok: false,
      code: 'EXTERNAL_ONLY',
      message: 'Cette offre se dépose sur le site de l’employeur. Le suivi de candidature n’est pas disponible pour ce dépôt.',
    }
  }

  const duplicate = existing.some(
    (a) => a.offerId === offer.id && a.candidateId === profile.id,
  )
  if (duplicate) {
    return { ok: false, code: 'DUPLICATE', message: 'Vous avez déjà une candidature en cours sur cette offre.' }
  }

  return { ok: true }
}

export type TransitionOutcome = { ok: true } | { ok: false; message: string }

/** Une transition absente de la machine à états est rejetée. */
export function checkTransition(
  current: ApplicationStatus,
  next: ApplicationStatus,
  role: RoleCode,
): TransitionOutcome {
  if (!canTransition(current, next, role)) {
    return {
      ok: false,
      message: 'Transition refusée : elle n’est pas autorisée depuis ce statut pour votre rôle.',
    }
  }
  return { ok: true }
}

/* ------------------------------------------------------------------ */
/* Simulations de traitements asynchrones                              */
/* ------------------------------------------------------------------ */

/** Analyse d'un CV importé : extraction puis OCR si le texte manque. */
export async function parseCV(fileName: string): Promise<{ ocrUsed: boolean; pageCount: number }> {
  const isImage = /\.(jpe?g|png|tiff?)$/i.test(fileName)
  return delay({ ocrUsed: isImage, pageCount: isImage ? 1 : 2 })
}

export { delay }
