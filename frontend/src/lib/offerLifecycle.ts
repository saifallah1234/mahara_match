// Placement: frontend/src/lib/offerLifecycle.ts
import type { OfferStatus } from './types'

export type OfferAction = { to: OfferStatus; label: string; confirm: boolean }

const ACTIONS: Record<OfferStatus, OfferAction[]> = {
  DRAFT: [
    { to: 'PUBLISHED', label: 'Publier', confirm: false },
    { to: 'ARCHIVED', label: 'Archiver', confirm: true },
  ],
  PUBLISHED: [
    { to: 'PAUSED', label: 'Mettre en pause', confirm: false },
    { to: 'CLOSED', label: 'Clôturer l’offre', confirm: true },
  ],
  PAUSED: [
    { to: 'PUBLISHED', label: 'Reprendre', confirm: false },
    { to: 'CLOSED', label: 'Clôturer l’offre', confirm: true },
  ],
  CLOSED: [{ to: 'ARCHIVED', label: 'Archiver', confirm: true }],
  ARCHIVED: [],
}

/** Transitions the backend allows from a status, labelled for the recruiter. */
export function offerActions(status: OfferStatus): OfferAction[] {
  return ACTIONS[status]
}
