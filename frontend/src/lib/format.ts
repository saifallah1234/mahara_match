import type {
  DeliveryMode,
  LanguageLevel,
  OfferStatus,
  RoleCode,
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

const CONTRACT_LABEL: Record<string, string> = {
  CDI: 'CDI',
  CDD: 'CDD',
  SIVP: 'SIVP',
  KARAMA: 'Karama',
  INTERNSHIP: 'Stage',
  FREELANCE: 'Freelance',
  SEASONAL: 'Saisonnier',
  FULL_TIME: 'Temps plein',
  PART_TIME: 'Temps partiel',
}

// shortcut: provisional vocabulary, replace when Q24 is settled
/** Contrats proposés à la saisie et au filtre ; les libellés d'import sont ajoutés pour l'affichage seul. */
export const CONTRACT_OPTIONS = ['CDI', 'CDD', 'SIVP', 'KARAMA', 'INTERNSHIP', 'FREELANCE', 'SEASONAL']

export function contractLabel(code?: string): string {
  return labelFor(CONTRACT_LABEL, code)
}

/** Les imports stockent déjà le libellé du site : il sert de valeur et d'étiquette. */
export const EXPERIENCE_OPTIONS = ['Débutant', '0 à 1 an', '1 à 3 ans', '3 à 5 ans', '5 à 10 ans']

export function experienceLabel(value?: string): string {
  return value || 'Non renseigné'
}

export const WORK_MODE_LABEL: Record<WorkMode, string> = {
  ONSITE: 'Sur site',
  HYBRID: 'Hybride',
  REMOTE: 'À distance',
}

// Backend codes (candidates.SkillLevel); the frontend's French SkillLevel type is not what the API sends.
export const SKILL_LEVEL_LABEL: Record<string, string> = {
  BEGINNER: 'Débutant',
  INTERMEDIATE: 'Intermédiaire',
  ADVANCED: 'Avancé',
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

export const OFFER_STATUS_TONE = { PUBLISHED: 'positif', DRAFT: 'neutre', PAUSED: 'attention', CLOSED: 'negatif', ARCHIVED: 'neutre' } as const

export const DELIVERY_LABEL: Record<DeliveryMode, string> = {
  PRESENTIEL: 'Présentiel',
  DISTANCIEL: 'À distance',
  HYBRIDE: 'Hybride',
}

/** Libellé d'un code d'API ; un code inconnu prend le repli fourni, jamais le code brut. */
export function labelFor(labels: Record<string, string>, code: string | null | undefined, fallback = 'Autre'): string {
  if (!code) return 'Non renseigné'
  return labels[code] ?? fallback
}

export const IMPORT_SOURCE_TYPE_LABEL: Record<string, string> = { API: 'API', CSV: 'Fichier CSV', MANUAL_FILE: 'Fichier saisi à la main', WEB_SCRAPING: 'Collecte web' }

export const IMPORT_BATCH_STATUS_LABEL: Record<string, string> = {
  STARTED: 'En cours',
  COMPLETED: 'Terminé',
  FAILED: 'Échoué',
}

export const IMPORT_ROW_STATUS_LABEL: Record<string, string> = {
  ADDED: 'Ajoutée', UPDATED: 'Mise à jour', UNCHANGED: 'Inchangée', REJECTED: 'Rejetée',
}

/** Codes émis par le pipeline d'import (pipelines/ingestion/offer_adapter.py). */
export const IMPORT_REJECTION_LABEL: Record<string, string> = {
  OFFER_CLOSED: 'Offre fermée ou expirée',
  MISSING_EXTERNAL_ID: 'Identifiant externe absent',
  INVALID_EXTERNAL_ID: 'Identifiant externe trop long',
  MISSING_TITLE: 'Titre absent',
  MISSING_DESCRIPTION: 'Description absente',
  INVALID_OFFER_URL: 'Lien de l’offre invalide',
  VALIDATION_ERROR: 'Données invalides',
}

export const AUDIT_ACTOR_LABEL: Record<string, string> = { USER: 'Utilisateur', SYSTEM: 'Système', ANETI_AGENT: 'Agent ANETI' }

export const AUDIT_ACTION_LABEL: Record<string, string> = {
  'imports.source.create': 'Source créée',
  'imports.source.update': 'Source modifiée',
  'imports.source.authorize': 'Source autorisée',
  'imports.source.revoke': 'Autorisation révoquée',
  'identity.user.create': 'Compte créé',
  'identity.user.status_change': 'Statut du compte modifié',
  'identity.user.delete': 'Compte supprimé',
  'identity.user_role.assign': 'Rôle attribué',
  'identity.user_role.remove': 'Rôle retiré',
  'identity.organization.verify': 'Organisation vérifiée',
  'identity.organization.reject': 'Organisation rejetée',
  'identity.onboarding.approve': 'Demande d’accès approuvée',
  'identity.onboarding.reject': 'Demande d’accès rejetée',
  'recruitment.application.submit': 'Candidature déposée',
  'recruitment.application.transition': 'Candidature changée d’étape',
  'recruitment.interview.finish': 'Entretien terminé',
  'training.enrollment.enroll': 'Inscription créée',
  'training.enrollment.progress': 'Progression mise à jour',
  'training.enrollment.cancel': 'Inscription annulée',
  'training.program.update': 'Programme modifié',
  'training.program.archive': 'Programme archivé',
  'training.session.update': 'Session modifiée',
}

export const AUDIT_ENTITY_LABEL: Record<string, string> = {
  data_sources: 'Source de données',
  user: 'Compte',
  user_role: 'Rôle',
  organization: 'Organisation',
  onboarding_request: 'Demande d’accès',
  application: 'Candidature',
  interview: 'Entretien',
  training_enrollment: 'Inscription',
  training_program: 'Programme',
  training_session: 'Session',
}

/** Statuts de session et étapes d'affichage de l'entretien blanc. */
export const MOCK_INTERVIEW_LABEL: Record<string, string> = {
  PREPARING: 'Préparation',
  READY: 'Prêt',
  INTRO: 'Introduction',
  SPEAKING: 'Question',
  LISTENING: 'Votre réponse',
  UPLOADING: 'Envoi de la réponse',
  IN_PROGRESS: 'En cours',
  THINKING: 'Analyse',
  EVALUATING: 'Évaluation',
  COMPLETED: 'Terminé',
  FAILED: 'Échec',
  CANCELLED: 'Annulé',
}

export const PROGRAM_STATUS_LABEL: Record<string, string> = { DRAFT: 'Brouillon', ACTIVE: 'Actif', ARCHIVED: 'Archivé' }

export const SESSION_STATUS_LABEL: Record<string, string> = {
  PLANNED: 'Planifiée',
  ONGOING: 'En cours',
  COMPLETED: 'Terminée',
  CANCELLED: 'Annulée',
}

export const ENROLLMENT_STATUS_LABEL: Record<string, string> = {
  REGISTERED: 'Inscrit',
  IN_PROGRESS: 'En cours',
  COMPLETED: 'Terminé',
  DROPPED: 'Abandonné',
}

export const INTERVIEW_TYPE_LABEL: Record<string, string> = {
  PHONE: 'Téléphonique',
  VIDEO: 'Visioconférence',
  IN_PERSON: 'Présentiel',
}

export const INTERVIEW_STATUS_LABEL: Record<string, string> = { SCHEDULED: 'Planifié', COMPLETED: 'Réalisé', CANCELLED: 'Annulé' }

/** Étapes et statuts des travaux d'un entretien blanc, affichés pendant le traitement. */
export const MOCK_JOB_STAGE_LABEL: Record<string, string> = {
  PREPARE: 'Préparation',
  TTS: 'Synthèse vocale',
  ANSWER: 'Analyse de la réponse',
  FOLLOWUP: 'Relance',
  ROUTE: 'Orientation',
  FEEDBACK: 'Retour',
  VIDEO_REQUIRED: 'Vidéo',
  VIDEO_BACKGROUND: 'Vidéo de fond',
}

export const MOCK_JOB_STATUS_LABEL: Record<string, string> = {
  PENDING: 'En attente',
  QUEUED: 'En file',
  RUNNING: 'En cours',
  SUCCEEDED: 'Réussi',
  RETRY_WAIT: 'Nouvel essai prévu',
  FAILED: 'Échec',
  CANCELLED: 'Annulé',
}

/** Codes d'erreur des traitements, traduits pour le candidat (jamais le code brut). */
export const MOCK_ERROR_LABEL: Record<string, string> = {
  stage_failed: 'le traitement a échoué. Vous pouvez réessayer.',
  worker_attempts_exhausted: 'la génération de la vidéo a échoué après plusieurs essais.',
}

export const MOCK_ERROR_FALLBACK = 'une erreur inattendue est survenue.'

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
  hourCycle: 'h23',
})

export function formatDate(iso?: string): string {
  if (!iso) return 'Non renseigné'
  return dateFormatter.format(new Date(iso))
}

export function formatDateTime(iso?: string): string {
  if (!iso) return 'Non renseigné'
  return dateTimeFormatter.format(new Date(iso))
}

/** Valeur d'un champ datetime-local, dans le fuseau du navigateur (là où la saisie l'interprète). */
export function toDateTimeInput(iso: string): string {
  const d = new Date(iso)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

const tunisDateTimeFormatter = new Intl.DateTimeFormat('fr-TN', {
  timeZone: 'Africa/Tunis',
  day: '2-digit',
  month: 'short',
  year: 'numeric',
  hour: '2-digit',
  minute: '2-digit',
  hour12: false,
  timeZoneName: 'short',
})

/** Interview times are shown on the Tunis clock, with its zone label, whatever the viewer's zone. */
export function formatTunisDateTime(iso?: string): string {
  if (!iso) return 'Non renseigné'
  return tunisDateTimeFormatter.format(new Date(iso))
}

export function formatMonthYear(iso?: string): string {
  if (!iso) return 'aujourd’hui'
  return new Intl.DateTimeFormat('fr-TN', { month: 'short', year: 'numeric' }).format(new Date(iso))
}

/** Les montants absents sont signalés, jamais devinés. */
export function formatSalary(min?: number, max?: number): string {
  if (min == null && max == null) return 'Non renseigné'
  if (min != null && max != null) return `${min.toLocaleString('fr-FR')} – ${max.toLocaleString('fr-FR')} TND / mois`
  const single = (min ?? max) as number
  return `${single.toLocaleString('fr-FR')} TND / mois`
}

/** A zero price means free (the training_programs check constraint ties price 0 to is_free). */
export function formatPrice(price?: number | string | null): string {
  if (price == null || price === '') return 'Non renseigné'
  const amount = Number(price)
  if (amount === 0) return 'Gratuit'
  return `${amount.toLocaleString('fr-FR')} TND`
}

/** Display-only: ESCO labels are stored lowercase and stay verbatim in the database. */
export function skillLabel(name: string): string {
  return name.charAt(0).toUpperCase() + name.slice(1)
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

const FIELD_LABEL: Record<string, string> = {
  title: 'Titre',
  description: 'Description',
  status: 'Statut',
  email: 'E-mail',
  capacity: 'Capacité',
  completion_rate: 'Taux d’achèvement',
  start_date: 'Date de début',
  end_date: 'Date de fin',
  registration_deadline: 'Date limite d’inscription',
  application_deadline: 'Date limite',
  location_or_url: 'Lieu ou lien',
  price: 'Prix',
  level: 'Niveau',
  delivery_mode: 'Modalité',
  contract_type: 'Contrat',
  work_mode: 'Mode de travail',
  experience_level: 'Expérience',
}

/** Messages de validation qui se traduisent sans ambiguïté ; les autres sont cités tels quels. */
function fieldMessage(messages: unknown): string {
  const first = Array.isArray(messages) ? String(messages[0] ?? '') : String(messages)
  if (first === 'Required.' || first === 'This field is required.') return 'ce champ est obligatoire.'
  if (first === 'This email is already in use.') return 'cette adresse e-mail est déjà utilisée.'
  return `valeur refusée (${first}).`
}

/** Erreurs API : code et champ traduits en français ; un message inconnu reste cité après une phrase générique. */
export function apiErrorMessage(code: string, message: string, details?: Record<string, unknown>): string {
  if (code === 'permission_denied') return 'Action non autorisée pour votre compte.'
  if (code === 'not_found') return 'Élément introuvable.'
  if (code === 'validation_error' && details && Object.keys(details).length > 0) {
    return Object.entries(details)
      .map(([field, messages]) => `${FIELD_LABEL[field] ?? 'Champ'} : ${fieldMessage(messages)}`)
      .join(' ')
  }
  if (code === 'validation_error' && message === 'Request validation failed.') return 'Les informations saisies ne sont pas valides.'
  return `Une erreur est survenue. (${message})`
}
