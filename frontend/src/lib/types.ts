/**
 * Types du domaine Mahara Match.
 *
 * Chaque interface reprend une table du modèle de données logique (MVP).
 * Les noms de champs sont en camelCase côté interface ; la correspondance
 * avec les colonnes PostgreSQL est indiquée en commentaire lorsqu'elle
 * n'est pas évidente.
 */

export type UUID = string

/* ------------------------------------------------------------------ */
/* A. Identité, rôles et organisations                                 */
/* ------------------------------------------------------------------ */

export type RoleCode =
  | 'CANDIDATE'
  | 'RECRUITER'
  | 'TRAINING_MANAGER'
  | 'MINISTRY_MANAGER'
  | 'ADMIN'

export type UserStatus = 'PENDING' | 'ACTIVE' | 'SUSPENDED' | 'DISABLED'

export interface User {
  id: UUID
  email: string
  firstName: string
  lastName: string
  phone?: string
  status: UserStatus
  emailVerifiedAt?: string
  lastLoginAt?: string
  roles: RoleCode[]
  roleAssignments?: Array<{ roleCode: RoleCode; organizationId?: UUID }>
  /** organisation de rattachement, nulle pour un rôle global (ADMIN) */
  organizationId?: UUID
  jobTitle?: string
}

export type OrganizationType =
  | 'COMPANY'
  | 'SUBSIDIARY'
  | 'TRAINING_PROVIDER'
  | 'MINISTRY'

export type VerificationStatus = 'PENDING' | 'VERIFIED' | 'REJECTED'

export interface Organization {
  id: UUID
  parentId?: UUID
  type: OrganizationType
  legalName: string
  /** matricule fiscal tunisien, 13 caractères */
  matriculeFiscal?: string
  description?: string
  websiteUrl?: string
  governorate?: string
  city?: string
  addressLine?: string
  verificationStatus: VerificationStatus
  createdAt: string
}

export interface Permission {
  code: string
  resource: string
  action: string
}

/* ------------------------------------------------------------------ */
/* B. Référentiels                                                     */
/* ------------------------------------------------------------------ */

export type SkillCategory = 'TECHNIQUE' | 'OUTIL' | 'METIER' | 'TRANSVERSALE' | 'LANGUE'

export interface Skill {
  id: UUID
  canonicalName: string
  category: SkillCategory
  description?: string
  /** libellés normalisés vers cette compétence (table skill_aliases) */
  aliases: string[]
}

export interface EducationLevel {
  id: UUID
  name: string
  levelOrder: number
}

export interface Language {
  id: UUID
  code: string
  name: string
}

/* ------------------------------------------------------------------ */
/* C. Profil candidat                                                  */
/* ------------------------------------------------------------------ */

export type ProfileVisibility = 'PRIVATE' | 'RECRUITERS' | 'PUBLIC'
export type SkillLevel = 'BEGINNER' | 'INTERMEDIATE' | 'ADVANCED' | 'EXPERT'
export type LanguageLevel = 'A1' | 'A2' | 'B1' | 'B2' | 'C1' | 'C2' | 'NATIF'
export type WorkMode = 'ONSITE' | 'HYBRID' | 'REMOTE'
export type Relocation = 'OPEN_TO_RELOCATE' | 'CANNOT_RELOCATE'
export type SkillSource = 'CV' | 'SAISIE' | 'FORMATION'

export interface Experience {
  id: UUID
  organizationName: string
  jobTitle: string
  startDate: string
  endDate?: string
  description?: string
}

export interface Education {
  id: UUID
  institution: string
  fieldOfStudy: string
  educationLevelId: UUID
  startYear: number
  endYear?: number
  description?: string
}

export interface Certification {
  id: UUID
  name: string
  certificationOrganization: string
  issueDate: string
  expirationDate?: string
  credentialId?: string
}

export interface Project {
  id: UUID
  name: string
  role: string
  description: string
  startDate: string
  endDate?: string
  technologies: string[]
  repositoryUrl?: string
}

export interface CandidateSkill {
  skillId: UUID
  level: SkillLevel
  yearsExperience: number
  /** confirmée par le candidat après extraction automatique */
  validated: boolean
  source: SkillSource
}

export interface CandidateLanguage {
  languageId: UUID
  level: LanguageLevel
}

export interface CandidateProfile {
  id: UUID
  userId: UUID
  birthDate?: string
  governorate?: string
  city?: string
  headline?: string
  summary?: string
  employmentStatus?: string
  desiredJobTitle?: string
  availabilityDate?: string
  profileVisibility: ProfileVisibility
  /** 0 à 100 */
  completionScore: number
  /** rayon accepté en kilomètres */
  maxDistanceKm: number
  relocation: Relocation
  preferredWorkMode: WorkMode
  experiences: Experience[]
  educations: Education[]
  certifications: Certification[]
  projects: Project[]
  skills: CandidateSkill[]
  languages: CandidateLanguage[]
}

/* ------------------------------------------------------------------ */
/* D. Documents et CV                                                  */
/* ------------------------------------------------------------------ */

export type ParseStatus = 'PENDING' | 'RUNNING' | 'PARSED' | 'FAILED'

export interface CVDocument {
  id: UUID
  candidateId: UUID
  title: string
  languageCode: string
  isPrimary: boolean
  parseStatus: ParseStatus
  versionNumber: number
  fileName: string
  sizeBytes: number
  uploadedAt: string
  /** true si le fichier a dû passer par l'OCR */
  ocrUsed: boolean
  pageCount: number
}

/** Champ proposé par l'extraction, avec sa provenance dans le document. */
export interface ExtractedField {
  id: string
  label: string
  value: string
  /** page du document d'où provient la valeur */
  sourcePage: number
  /** extrait brut du texte reconnu */
  sourceExcerpt: string
  /** 0 à 1 */
  confidence: number
  status: 'PROPOSED' | 'CONFIRMED' | 'CORRECTED'
  correctedValue?: string
}

export interface ATSCheck {
  code: string
  label: string
  passed: boolean
  detail: string
}

export interface CVAnalysisResult {
  id: UUID
  cvId: UUID
  targetOfferId?: UUID
  overallScore: number
  checks: ATSCheck[]
  suggestions: string[]
  analyzedAt: string
}

/* ------------------------------------------------------------------ */
/* E. Offres et recrutement                                            */
/* ------------------------------------------------------------------ */

export type ContractType = 'CDI' | 'CDD' | 'STAGE' | 'ALTERNANCE' | 'FREELANCE' | 'SIVP'
export type ExperienceLevel = 'DEBUTANT' | 'JUNIOR' | 'CONFIRME' | 'SENIOR'
export type OfferStatus = 'DRAFT' | 'PUBLISHED' | 'PAUSED' | 'CLOSED' | 'ARCHIVED'
export type SkillImportance = 'OBLIGATOIRE' | 'SOUHAITEE'

/** Pondération du calcul de couverture : poids 2 obligatoire, poids 1 souhaitée. */
export const SKILL_WEIGHT: Record<SkillImportance, number> = {
  OBLIGATOIRE: 2,
  SOUHAITEE: 1,
}

export interface OfferSkill {
  skillId: UUID
  importance: SkillImportance
  requiredLevel: SkillLevel
}

export interface JobOffer {
  id: UUID
  reference: string
  organizationId: UUID
  createdBy: UUID
  title: string
  description: string
  contractType: ContractType
  workMode: WorkMode
  governorate: string
  city: string
  experienceLevel: ExperienceLevel
  minSalary?: number
  maxSalary?: number
  applicationDeadline?: string
  status: OfferStatus
  publishedAt?: string
  closedAt?: string
  /** candidature possible sur la plateforme ; sinon dépôt externe non suivi */
  easyApply: boolean
  externalUrl?: string
  educationLevelId?: UUID
  requiredLanguageId?: UUID
  skills: OfferSkill[]
  /** renseigné quand l'offre provient d'un import */
  sourceId?: UUID
  externalId?: string
}

/* ------------------------------------------------------------------ */
/* F. Candidatures                                                     */
/* ------------------------------------------------------------------ */

export type ApplicationStatus =
  | 'SUBMITTED'
  | 'UNDER_REVIEW'
  | 'PRESELECTED'
  | 'INTERVIEW'
  | 'OFFERED'
  | 'HIRED'
  | 'REJECTED'
  | 'WITHDRAWN'

export interface StatusHistoryEntry {
  id: UUID
  status: ApplicationStatus
  reason?: string
  changedAt: string
  changedByRole: RoleCode
}

export type InterviewType = 'TELEPHONE' | 'VISIO' | 'PRESENTIEL'
export type InterviewStatus = 'PLANIFIE' | 'REALISE' | 'ANNULE'

export interface Interview {
  id: UUID
  applicationId: UUID
  type: InterviewType
  scheduledAt: string
  durationMinutes: number
  locationOrUrl: string
  status: InterviewStatus
  feedback?: string
}

export interface Application {
  id: UUID
  candidateId: UUID
  offerId: UUID
  /** version de CV figée au moment du dépôt */
  cvId: UUID
  status: ApplicationStatus
  coverLetter?: string
  appliedAt: string
  withdrawnAt?: string
  history: StatusHistoryEntry[]
}

/* ------------------------------------------------------------------ */
/* G. Formations                                                       */
/* ------------------------------------------------------------------ */

export type DeliveryMode = 'PRESENTIEL' | 'DISTANCIEL' | 'HYBRIDE'
export type ProgramStatus = 'DRAFT' | 'PUBLISHED' | 'ARCHIVED'
export type SessionStatus = 'PLANIFIEE' | 'OUVERTE' | 'COMPLETE' | 'TERMINEE' | 'ANNULEE'
export type EnrollmentStatus = 'INSCRIT' | 'EN_COURS' | 'TERMINE' | 'ABANDONNE'

export interface TrainingProgram {
  id: UUID
  organizationId: UUID
  title: string
  description: string
  level: SkillLevel
  deliveryMode: DeliveryMode
  status: ProgramStatus
  durationHours: number
  /** non renseigné si l'organisme ne l'a pas fourni */
  priceTnd?: number
  prerequisites: string
  contactEmail: string
  /** compétences visées (table training_skills) */
  skillIds: UUID[]
}

export interface TrainingSession {
  id: UUID
  programId: UUID
  startDate: string
  endDate: string
  capacity: number
  locationOrUrl: string
  registrationDeadline: string
  status: SessionStatus
}

export interface TrainingEnrollment {
  id: UUID
  sessionId: UUID
  candidateId: UUID
  status: EnrollmentStatus
  enrolledAt: string
  completionRate: number
}

/* ------------------------------------------------------------------ */
/* H. Agent conversationnel                                            */
/* ------------------------------------------------------------------ */

export type AgentLocale = 'fr' | 'ar' | 'tn'
export type MessageSender = 'USER' | 'AGENT'

export interface Citation {
  label: string
  reference: string
}

/** Action métier proposée par l'agent, exécutée après confirmation. */
export interface AgentAction {
  type: 'POSTULER'
  offerId: UUID
  cvId: UUID
  coverLetter: string
  status: 'PROPOSED' | 'CONFIRMED' | 'CANCELLED' | 'BLOCKED'
  blockedReason?: string
}

export interface ConversationMessage {
  id: UUID
  sender: MessageSender
  content: string
  citations?: Citation[]
  action?: AgentAction
  createdAt: string
}

/* ------------------------------------------------------------------ */
/* I. Imports et audit                                                 */
/* ------------------------------------------------------------------ */

export type SourceType = 'API' | 'CSV' | 'MANUAL_FILE'
export type BatchStatus = 'RUNNING' | 'COMPLETED' | 'FAILED'
export type RowStatus = 'ADDED' | 'UPDATED' | 'UNCHANGED' | 'REJECTED'

export interface DataSource {
  id: UUID
  name: string
  type: SourceType
  baseUrl?: string
  isAuthorized: boolean
}

export interface ImportBatch {
  id: UUID
  sourceId: UUID
  checksum: string
  status: BatchStatus
  startedAt: string
  completedAt?: string
  addedCount: number
  updatedCount: number
  unchangedCount: number
  rejectedCount: number
}

export interface ImportRow {
  id: UUID
  batchId: UUID
  rowNumber: number
  externalId?: string
  status: RowStatus
  errorCode?: string
  errorMessage?: string
}

export interface AuditLog {
  id: UUID
  actorLabel: string
  actorKind: 'UTILISATEUR' | 'AGENT_IA' | 'SYSTEME'
  action: string
  entityType: string
  entityId: string
  createdAt: string
  ipAddress?: string
}

export interface Notification {
  id: UUID
  userId: UUID
  title: string
  body: string
  createdAt: string
  readAt?: string
}
