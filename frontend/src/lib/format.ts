import type {
  ContractType,
  DeliveryMode,
  ExperienceLevel,
  LanguageLevel,
  OfferStatus,
  RoleCode,
  SkillLevel,
  WorkMode,
} from './types'

export const ROLE_LABEL: Record<RoleCode, string> = {
  CANDIDATE: 'Chercheur d’emploi',
  RECRUITER: 'Employeur / Recruteur',
  TRAINING_MANAGER: 'Organisme de formation',
  MINISTRY_MANAGER: 'Responsable du ministère',
  ADMIN: 'Administrateur',
}

export const ROLE_HOME: Record<RoleCode, string> = {
  CANDIDATE: '/candidat',
  RECRUITER: '/recruteur',
  TRAINING_MANAGER: '/formation',
  MINISTRY_MANAGER: '/ministere',
  ADMIN: '/admin',
}

export const CONTRACT_LABEL: Record<ContractType, string> = {
  CDI: 'CDI',
  CDD: 'CDD',
  STAGE: 'Stage',
  ALTERNANCE: 'Alternance',
  FREELANCE: 'Freelance',
  SIVP: 'SIVP',
}

export const WORK_MODE_LABEL: Record<WorkMode, string> = {
  ONSITE: 'Sur site',
  HYBRID: 'Hybride',
  REMOTE: 'À distance',
}

export const EXPERIENCE_LABEL: Record<ExperienceLevel, string> = {
  DEBUTANT: 'Débutant',
  JUNIOR: 'Junior',
  CONFIRME: 'Confirmé',
  SENIOR: 'Senior',
}

export const SKILL_LEVEL_LABEL: Record<SkillLevel, string> = {
  DEBUTANT: 'Débutant',
  INTERMEDIAIRE: 'Intermédiaire',
  AVANCE: 'Avancé',
  EXPERT: 'Expert',
}

export const LANGUAGE_LEVEL_LABEL: Record<LanguageLevel, string> = {
  A1: 'A1',
  A2: 'A2',
  B1: 'B1',
  B2: 'B2',
  C1: 'C1',
  C2: 'C2',
  NATIF: 'Langue maternelle',
}

export const OFFER_STATUS_LABEL: Record<OfferStatus, string> = {
  DRAFT: 'Brouillon',
  PUBLISHED: 'Publiée',
  PAUSED: 'En pause',
  CLOSED: 'Clôturée',
  ARCHIVED: 'Archivée',
}

export const DELIVERY_LABEL: Record<DeliveryMode, string> = {
  PRESENTIEL: 'Présentiel',
  DISTANCIEL: 'À distance',
  HYBRIDE: 'Hybride',
}

export const GOUVERNORATS = [
  'Ariana',
  'Béja',
  'Ben Arous',
  'Bizerte',
  'Gabès',
  'Gafsa',
  'Jendouba',
  'Kairouan',
  'Kasserine',
  'Kébili',
  'La Manouba',
  'Le Kef',
  'Mahdia',
  'Médenine',
  'Monastir',
  'Nabeul',
  'Sfax',
  'Sidi Bouzid',
  'Siliana',
  'Sousse',
  'Tataouine',
  'Tozeur',
  'Tunis',
  'Zaghouan',
]

const dateFormatter = new Intl.DateTimeFormat('fr-TN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
})

const dateTimeFormatter = new Intl.DateTimeFormat('fr-TN', {
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
})

export function formatDate(iso?: string): string {
  if (!iso) return 'Non renseigné'
  return dateFormatter.format(new Date(iso))
}

export function formatDateTime(iso?: string): string {
  if (!iso) return 'Non renseigné'
  return dateTimeFormatter.format(new Date(iso))
}

export function formatMonthYear(iso?: string): string {
  if (!iso) return 'aujourd’hui'
  return new Intl.DateTimeFormat('fr-TN', { month: 'short', year: 'numeric' }).format(new Date(iso))
}

/** Les montants absents sont signalés, jamais devinés. */
export function formatSalary(min?: number, max?: number): string {
  if (min == null && max == null) return 'Non renseigné'
  if (min != null && max != null) return `${min.toLocaleString('fr-FR')} – ${max.toLocaleString('fr-FR')} DT / mois`
  const single = (min ?? max) as number
  return `${single.toLocaleString('fr-FR')} DT / mois`
}

export function formatPrice(price?: number): string {
  if (price == null) return 'Non renseigné'
  if (price === 0) return 'Gratuit'
  return `${price.toLocaleString('fr-FR')} DT`
}

export function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} o`
  if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} Ko`
  return `${(bytes / (1024 * 1024)).toFixed(1)} Mo`
}

export function relativeDays(iso: string): string {
  const diff = Math.round((Date.now() - new Date(iso).getTime()) / 86_400_000)
  if (diff <= 0) return 'aujourd’hui'
  if (diff === 1) return 'hier'
  if (diff < 30) return `il y a ${diff} jours`
  const months = Math.round(diff / 30)
  return months === 1 ? 'il y a 1 mois' : `il y a ${months} mois`
}

/** Évite « Ariana, Ariana » quand la ville porte le nom du gouvernorat. */
export function formatPlace(city?: string, governorate?: string): string {
  if (!city) return governorate ?? 'Non renseigné'
  if (!governorate || city === governorate) return city
  return `${city}, ${governorate}`
}

export function initials(firstName: string, lastName: string): string {
  return `${firstName.charAt(0)}${lastName.charAt(0)}`.toUpperCase()
}

export function cx(...parts: Array<string | false | null | undefined>): string {
  return parts.filter(Boolean).join(' ')
}
