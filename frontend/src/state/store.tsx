import {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import {
  APPLICATIONS,
  AUDIT_LOGS,
  CANDIDATE_PROFILES,
  CVS,
  CV_ANALYSES,
  DATA_SOURCES,
  IMPORT_BATCHES,
  IMPORT_ROWS,
  INTERVIEWS,
  JOB_OFFERS,
  NOTIFICATIONS,
  ORGANIZATIONS,
  TRAINING_ENROLLMENTS,
  TRAINING_PROGRAMS,
  TRAINING_SESSIONS,
  USERS,
} from '../data/seed'
import { SKILLS } from '../data/referentials'
import type {
  Application,
  ApplicationStatus,
  AuditLog,
  CandidateProfile,
  CVDocument,
  JobOffer,
  Organization,
  RoleCode,
  TrainingEnrollment,
  TrainingProgram,
  TrainingSession,
  User,
  UUID,
} from '../lib/types'
import { checkApply, checkTransition } from '../api/client'

interface Session {
  user: User
  role: RoleCode
}

interface Toast {
  id: number
  tone: 'succes' | 'echec' | 'info'
  message: string
}

interface StoreValue {
  /* Données */
  users: User[]
  organizations: Organization[]
  profiles: CandidateProfile[]
  cvs: CVDocument[]
  offers: JobOffer[]
  applications: Application[]
  interviews: typeof INTERVIEWS
  programs: TrainingProgram[]
  sessions: TrainingSession[]
  enrollments: TrainingEnrollment[]
  analyses: typeof CV_ANALYSES
  sources: typeof DATA_SOURCES
  batches: typeof IMPORT_BATCHES
  rows: typeof IMPORT_ROWS
  auditLogs: AuditLog[]
  notifications: typeof NOTIFICATIONS
  skills: typeof SKILLS

  /* Session */
  session: Session | null
  signIn: (userId: UUID, role: RoleCode) => void
  signOut: () => void

  /* Sélecteurs */
  currentProfile: CandidateProfile | null
  organizationOf: (id?: UUID) => Organization | undefined
  userOf: (id: UUID) => User | undefined
  profileOf: (id: UUID) => CandidateProfile | undefined
  offerOf: (id: UUID) => JobOffer | undefined
  cvOf: (id: UUID) => CVDocument | undefined

  /* Actions */
  apply: (offerId: UUID, cvId: UUID, coverLetter: string) => { ok: boolean; message: string }
  transition: (applicationId: UUID, next: ApplicationStatus, reason?: string) => { ok: boolean; message: string }
  updateProfile: (patch: Partial<CandidateProfile>) => void
  validateSkill: (skillId: UUID) => void
  publishOffer: (offer: JobOffer) => void
  closeOffer: (offerId: UUID) => void
  enroll: (sessionId: UUID) => { ok: boolean; message: string }
  publishProgram: (program: TrainingProgram) => void
  verifyOrganization: (orgId: UUID, decision: 'VERIFIED' | 'REJECTED') => void
  setUserStatus: (userId: UUID, status: User['status']) => void
  addSkillAlias: (skillId: UUID, alias: string) => void

  /* Retours visuels */
  toasts: Toast[]
  dismissToast: (id: number) => void
}

const StoreContext = createContext<StoreValue | null>(null)

let toastSeq = 0
let idSeq = 0
const nextId = (prefix: string) => `${prefix}-${Date.now().toString(36)}-${idSeq++}`

export function StoreProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>(USERS)
  const [organizations, setOrganizations] = useState<Organization[]>(ORGANIZATIONS)
  const [profiles, setProfiles] = useState<CandidateProfile[]>(CANDIDATE_PROFILES)
  const [cvs] = useState<CVDocument[]>(CVS)
  const [offers, setOffers] = useState<JobOffer[]>(JOB_OFFERS)
  const [applications, setApplications] = useState<Application[]>(APPLICATIONS)
  const [interviews] = useState(INTERVIEWS)
  const [programs, setPrograms] = useState<TrainingProgram[]>(TRAINING_PROGRAMS)
  const [sessions] = useState<TrainingSession[]>(TRAINING_SESSIONS)
  const [enrollments, setEnrollments] = useState<TrainingEnrollment[]>(TRAINING_ENROLLMENTS)
  const [skills, setSkills] = useState(SKILLS)
  const [auditLogs, setAuditLogs] = useState<AuditLog[]>(AUDIT_LOGS)
  const [session, setSession] = useState<Session | null>(null)
  const [toasts, setToasts] = useState<Toast[]>([])

  const pushToast = useCallback((tone: Toast['tone'], message: string) => {
    const id = ++toastSeq
    setToasts((list) => [...list, { id, tone, message }])
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), 5000)
  }, [])

  const dismissToast = useCallback((id: number) => {
    setToasts((list) => list.filter((t) => t.id !== id))
  }, [])

  /** Toute opération sensible laisse une trace, y compris celles de l'agent. */
  const trace = useCallback(
    (action: string, entityType: string, entityId: string, actorKind: AuditLog['actorKind'] = 'UTILISATEUR') => {
      setSession((current) => {
        const label = current ? `${current.user.firstName} ${current.user.lastName}` : 'Système'
        setAuditLogs((logs) => [
          { id: nextId('al'), actorLabel: actorKind === 'AGENT_IA' ? 'Agent conversationnel' : label, actorKind, action, entityType, entityId, createdAt: new Date().toISOString() },
          ...logs,
        ])
        return current
      })
    },
    [],
  )

  const signIn = useCallback((userId: UUID, role: RoleCode) => {
    const user = USERS.find((u) => u.id === userId)
    if (user) setSession({ user, role })
  }, [])

  const signOut = useCallback(() => setSession(null), [])

  const userOf = useCallback((id: UUID) => users.find((u) => u.id === id), [users])
  const profileOf = useCallback((id: UUID) => profiles.find((p) => p.id === id), [profiles])
  const offerOf = useCallback((id: UUID) => offers.find((o) => o.id === id), [offers])
  const cvOf = useCallback((id: UUID) => cvs.find((c) => c.id === id), [cvs])
  const organizationOf = useCallback(
    (id?: UUID) => (id ? organizations.find((o) => o.id === id) : undefined),
    [organizations],
  )

  const currentProfile = useMemo(() => {
    if (!session || session.role !== 'CANDIDATE') return null
    return profiles.find((p) => p.userId === session.user.id) ?? null
  }, [session, profiles])

  const apply = useCallback<StoreValue['apply']>(
    (offerId, cvId, coverLetter) => {
      const offer = offers.find((o) => o.id === offerId)
      const profile = currentProfile
      if (!offer || !profile) return { ok: false, message: 'Offre ou profil introuvable.' }

      const verdict = checkApply({ profile, offer, cvId, coverLetter, existing: applications })
      if (!verdict.ok) {
        pushToast('echec', verdict.message)
        return { ok: false, message: verdict.message }
      }

      const now = new Date().toISOString()
      const application: Application = {
        id: nextId('ap'),
        candidateId: profile.id,
        offerId,
        cvId,
        status: 'SUBMITTED',
        coverLetter,
        appliedAt: now,
        history: [{ id: nextId('h'), status: 'SUBMITTED', changedAt: now, changedByRole: 'CANDIDATE' }],
      }
      setApplications((list) => [application, ...list])
      trace('Dépôt de candidature', 'Candidature', application.id)
      pushToast('succes', 'Candidature déposée. Le recruteur a été notifié.')
      return { ok: true, message: 'Candidature déposée.' }
    },
    [offers, currentProfile, applications, pushToast, trace],
  )

  const transition = useCallback<StoreValue['transition']>(
    (applicationId, next, reason) => {
      if (!session) return { ok: false, message: 'Session expirée.' }
      const application = applications.find((a) => a.id === applicationId)
      if (!application) return { ok: false, message: 'Candidature introuvable.' }

      const verdict = checkTransition(application.status, next, session.role)
      if (!verdict.ok) {
        pushToast('echec', verdict.message)
        return { ok: false, message: verdict.message }
      }

      const now = new Date().toISOString()
      setApplications((list) =>
        list.map((a) =>
          a.id === applicationId
            ? {
                ...a,
                status: next,
                withdrawnAt: next === 'WITHDRAWN' ? now : a.withdrawnAt,
                history: [...a.history, { id: nextId('h'), status: next, reason, changedAt: now, changedByRole: session.role }],
              }
            : a,
        ),
      )
      trace('Changement de statut de candidature', 'Candidature', applicationId)
      pushToast('succes', 'Statut mis à jour. Le changement est consigné dans l’historique.')
      return { ok: true, message: 'Statut mis à jour.' }
    },
    [session, applications, pushToast, trace],
  )

  const updateProfile = useCallback<StoreValue['updateProfile']>(
    (patch) => {
      if (!currentProfile) return
      setProfiles((list) => list.map((p) => (p.id === currentProfile.id ? { ...p, ...patch } : p)))
      pushToast('succes', 'Profil enregistré.')
    },
    [currentProfile, pushToast],
  )

  const validateSkill = useCallback<StoreValue['validateSkill']>(
    (skillId) => {
      if (!currentProfile) return
      setProfiles((list) =>
        list.map((p) =>
          p.id === currentProfile.id
            ? { ...p, skills: p.skills.map((s) => (s.skillId === skillId ? { ...s, validated: true } : s)) }
            : p,
        ),
      )
      pushToast('succes', 'Compétence confirmée. Elle compte désormais dans vos correspondances.')
    },
    [currentProfile, pushToast],
  )

  const publishOffer = useCallback<StoreValue['publishOffer']>(
    (offer) => {
      setOffers((list) => {
        const exists = list.some((o) => o.id === offer.id)
        return exists ? list.map((o) => (o.id === offer.id ? offer : o)) : [offer, ...list]
      })
      trace(offer.status === 'PUBLISHED' ? 'Publication d’une offre' : 'Enregistrement d’un brouillon d’offre', 'Offre', offer.id)
      pushToast('succes', offer.status === 'PUBLISHED' ? 'Offre publiée.' : 'Brouillon enregistré.')
    },
    [pushToast, trace],
  )

  const closeOffer = useCallback<StoreValue['closeOffer']>(
    (offerId) => {
      setOffers((list) =>
        list.map((o) => (o.id === offerId ? { ...o, status: 'CLOSED', closedAt: new Date().toISOString() } : o)),
      )
      trace('Clôture d’une offre', 'Offre', offerId)
      pushToast('succes', 'Offre clôturée. Elle disparaît des nouveaux résultats.')
    },
    [pushToast, trace],
  )

  const enroll = useCallback<StoreValue['enroll']>(
    (sessionId) => {
      if (!currentProfile) return { ok: false, message: 'Profil introuvable.' }
      const already = enrollments.some((e) => e.sessionId === sessionId && e.candidateId === currentProfile.id)
      if (already) {
        pushToast('echec', 'Vous êtes déjà inscrite à cette session.')
        return { ok: false, message: 'Inscription déjà enregistrée.' }
      }
      setEnrollments((list) => [
        { id: nextId('te'), sessionId, candidateId: currentProfile.id, status: 'INSCRIT', enrolledAt: new Date().toISOString(), completionRate: 0 },
        ...list,
      ])
      pushToast('succes', 'Inscription enregistrée auprès de l’organisme.')
      return { ok: true, message: 'Inscription enregistrée.' }
    },
    [currentProfile, enrollments, pushToast],
  )

  const publishProgram = useCallback<StoreValue['publishProgram']>(
    (program) => {
      setPrograms((list) => {
        const exists = list.some((p) => p.id === program.id)
        return exists ? list.map((p) => (p.id === program.id ? program : p)) : [program, ...list]
      })
      trace('Publication d’une formation', 'Formation', program.id)
      pushToast('succes', program.status === 'PUBLISHED' ? 'Formation publiée au catalogue.' : 'Brouillon enregistré.')
    },
    [pushToast, trace],
  )

  const verifyOrganization = useCallback<StoreValue['verifyOrganization']>(
    (orgId, decision) => {
      setOrganizations((list) => list.map((o) => (o.id === orgId ? { ...o, verificationStatus: decision } : o)))
      trace('Vérification d’organisation', 'Organisation', orgId)
      pushToast('succes', decision === 'VERIFIED' ? 'Organisation vérifiée.' : 'Organisation rejetée.')
    },
    [pushToast, trace],
  )

  const setUserStatus = useCallback<StoreValue['setUserStatus']>(
    (userId, status) => {
      setUsers((list) => list.map((u) => (u.id === userId ? { ...u, status } : u)))
      trace('Changement de statut de compte', 'Compte', userId)
      pushToast('succes', 'Statut du compte mis à jour.')
    },
    [pushToast, trace],
  )

  const addSkillAlias = useCallback<StoreValue['addSkillAlias']>(
    (skillId, alias) => {
      setSkills((list) =>
        list.map((s) => (s.id === skillId && !s.aliases.includes(alias) ? { ...s, aliases: [...s.aliases, alias] } : s)),
      )
      trace('Ajout d’un alias au référentiel des compétences', 'Compétence', skillId)
      pushToast('succes', `« ${alias} » est désormais normalisé.`)
    },
    [pushToast, trace],
  )

  const value: StoreValue = {
    users,
    organizations,
    profiles,
    cvs,
    offers,
    applications,
    interviews,
    programs,
    sessions,
    enrollments,
    analyses: CV_ANALYSES,
    sources: DATA_SOURCES,
    batches: IMPORT_BATCHES,
    rows: IMPORT_ROWS,
    auditLogs,
    notifications: NOTIFICATIONS,
    skills,
    session,
    signIn,
    signOut,
    currentProfile,
    organizationOf,
    userOf,
    profileOf,
    offerOf,
    cvOf,
    apply,
    transition,
    updateProfile,
    validateSkill,
    publishOffer,
    closeOffer,
    enroll,
    publishProgram,
    verifyOrganization,
    setUserStatus,
    addSkillAlias,
    toasts,
    dismissToast,
  }

  return <StoreContext.Provider value={value}>{children}</StoreContext.Provider>
}

export function useStore(): StoreValue {
  const value = useContext(StoreContext)
  if (!value) throw new Error('useStore doit être utilisé à l’intérieur de StoreProvider.')
  return value
}
