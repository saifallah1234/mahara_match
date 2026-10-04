/**
 * Point de bascule vers le backend réel.
 *
 * Aujourd'hui les données viennent d'un jeu de démonstration en mémoire
 * (src/data/seed.ts). Pour brancher l'API, remplacer le corps de chaque
 * fonction par un appel `request(...)` : les signatures et les types de
 * retour ne changent pas, donc aucune page n'est à modifier.
 *
 *   export async function listOffers() {
 *     return request<JobOffer[]>('/offers')
 *   }
 */

import type {
  Application,
  ApplicationStatus,
  CandidateProfile,
  JobOffer,
  RoleCode,
  UUID,
} from '../lib/types'
import { canTransition } from '../lib/statusMachine'

export const API_BASE_URL = import.meta.env.VITE_API_URL ?? '/api/v1'

/** Latence simulée, pour que les états de chargement soient visibles. */
const LATENCY_MS = 220

function delay<T>(value: T): Promise<T> {
  return new Promise((resolve) => setTimeout(() => resolve(value), LATENCY_MS))
}

/** Transport HTTP, prêt à l'emploi quand le backend sera disponible. */
export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(init?.headers ?? {}),
    },
  })

  if (!response.ok) {
    const payload = await response.json().catch(() => ({}))
    throw new ApiError(response.status, payload.code ?? 'UNKNOWN', payload.message ?? response.statusText)
  }

  return response.json() as Promise<T>
}

export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
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
    (a) => a.offerId === offer.id && a.candidateId === profile.id && a.status !== 'WITHDRAWN',
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
