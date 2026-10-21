/**
 * Machine à états de la candidature.
 *
 * Le cycle reprend celui de la présentation du projet :
 *   Soumise → En examen → Présélectionnée → Entretien → Proposée → Recrutée
 * avec deux sorties : Refusée (recruteur) et Retirée (candidat).
 *
 * Chaque transition vérifie le rôle de l'auteur et le statut courant.
 * Une transition absente de cette table est refusée par le service métier.
 */

import type { ApplicationStatus, RoleCode } from './types'

export const APPLICATION_FLOW: ApplicationStatus[] = [
  'SUBMITTED',
  'UNDER_REVIEW',
  'PRESELECTED',
  'INTERVIEW',
  'OFFERED',
  'HIRED',
]

export const TERMINAL_STATUSES: ApplicationStatus[] = ['HIRED', 'REJECTED', 'WITHDRAWN']

export const STATUS_LABEL: Record<ApplicationStatus, string> = {
  SUBMITTED: 'Soumise',
  UNDER_REVIEW: 'En examen',
  PRESELECTED: 'Présélectionnée',
  INTERVIEW: 'Entretien',
  OFFERED: 'Proposée',
  HIRED: 'Recrutée',
  REJECTED: 'Refusée',
  WITHDRAWN: 'Retirée',
}

/** Verbe de l'action, pour que le bouton annonce ce qu'il fait. */
export const TRANSITION_LABEL: Partial<Record<ApplicationStatus, string>> = {
  UNDER_REVIEW: 'Ouvrir l’examen',
  PRESELECTED: 'Présélectionner',
  INTERVIEW: 'Proposer un entretien',
  OFFERED: 'Faire une proposition',
  HIRED: 'Déclarer le recrutement',
  REJECTED: 'Refuser',
  WITHDRAWN: 'Retirer ma candidature',
}

interface Transition {
  to: ApplicationStatus
  /** rôles autorisés à déclencher cette transition */
  allowedRoles: RoleCode[]
}

const TRANSITIONS: Record<ApplicationStatus, Transition[]> = {
  SUBMITTED: [
    { to: 'UNDER_REVIEW', allowedRoles: ['RECRUITER'] },
    { to: 'REJECTED', allowedRoles: ['RECRUITER'] },
    { to: 'WITHDRAWN', allowedRoles: ['CANDIDATE'] },
  ],
  UNDER_REVIEW: [
    { to: 'PRESELECTED', allowedRoles: ['RECRUITER'] },
    { to: 'REJECTED', allowedRoles: ['RECRUITER'] },
    { to: 'WITHDRAWN', allowedRoles: ['CANDIDATE'] },
  ],
  PRESELECTED: [
    { to: 'INTERVIEW', allowedRoles: ['RECRUITER'] },
    { to: 'REJECTED', allowedRoles: ['RECRUITER'] },
    { to: 'WITHDRAWN', allowedRoles: ['CANDIDATE'] },
  ],
  INTERVIEW: [
    { to: 'OFFERED', allowedRoles: ['RECRUITER'] },
    { to: 'REJECTED', allowedRoles: ['RECRUITER'] },
    { to: 'WITHDRAWN', allowedRoles: ['CANDIDATE'] },
  ],
  OFFERED: [
    { to: 'HIRED', allowedRoles: ['RECRUITER'] },
    { to: 'REJECTED', allowedRoles: ['RECRUITER'] },
    { to: 'WITHDRAWN', allowedRoles: ['CANDIDATE'] },
  ],
  HIRED: [],
  REJECTED: [],
  WITHDRAWN: [],
}

export function allowedTransitions(
  current: ApplicationStatus,
  role: RoleCode,
): ApplicationStatus[] {
  return TRANSITIONS[current]
    .filter((t) => t.allowedRoles.includes(role))
    .map((t) => t.to)
}

export function canTransition(
  current: ApplicationStatus,
  next: ApplicationStatus,
  role: RoleCode,
): boolean {
  return allowedTransitions(current, role).includes(next)
}

export function isTerminal(status: ApplicationStatus): boolean {
  return TERMINAL_STATUSES.includes(status)
}

/** Position dans le cycle nominal, utilisée par la frise de suivi. */
export function flowIndex(status: ApplicationStatus): number {
  const index = APPLICATION_FLOW.indexOf(status)
  if (index >= 0) return index
  return -1
}

/** Stages after the current one on the flow; a recruiter may skip optional ones. */
export function laterStages(status: ApplicationStatus): ApplicationStatus[] {
  const index = flowIndex(status)
  return index < 0 ? [] : APPLICATION_FLOW.slice(index + 1)
}

export type StatusTone = 'neutre' | 'encours' | 'positif' | 'negatif'

export function statusTone(status: ApplicationStatus): StatusTone {
  switch (status) {
    case 'HIRED':
      return 'positif'
    case 'REJECTED':
    case 'WITHDRAWN':
      return 'negatif'
    case 'SUBMITTED':
      return 'neutre'
    default:
      return 'encours'
  }
}
