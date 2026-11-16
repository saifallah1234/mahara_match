import { allPages } from './auth.ts'
import { request } from './client.ts'

export type RecruiterOffer = {
  id: string; organization_id: string; organization_name: string; company_name: string; title: string; description: string
  contract_type: string; work_mode: string; experience_level: string; governorate: string; city: string
  min_salary: string | null; max_salary: string | null; application_deadline: string | null
  status: 'DRAFT' | 'PUBLISHED' | 'PAUSED' | 'CLOSED' | 'ARCHIVED'; published_at: string | null
  easy_apply: boolean; offer_url: string; created_by_id: string
}
export type OfferSkill = { id: string; offer_id: string; skill_id: string; is_mandatory: boolean; importance: string }
export type Applicant = { first_name: string; last_name: string; email: string }
export type RecruiterApplication = {
  id: string; candidate_id: string; applicant: Applicant
  offer_id: string; offer_title: string; cv_id: string; status: string; cover_letter: string; applied_at: string
}
export type StatusHistory = { id: string; application_id: string; status: string; reason: string; changed_at: string }
export type RecruiterInterview = {
  id: string; application_id: string; type: 'IN_PERSON' | 'VIDEO' | 'PHONE'; scheduled_at: string
  duration_minutes: number; location_or_url: string; status: 'SCHEDULED' | 'COMPLETED' | 'CANCELLED'; feedback: string
}
export type SkillRef = { id: string; canonical_name: string; category?: string }
export type EducationLevel = { id: string; name: string; level_order: number }
/** Redacted profile served to verified recruiters (RecruiterCandidateSerializer). Decimals arrive as strings. */
export type CandidateCard = {
  id: string; headline: string; governorate: string
  skills: { skill: string; level: string; years_experience: string | null }[]
  experiences: { organization_name: string; job_title: string; start_date: string; end_date: string | null }[]
  educations: { education_level: string; institution: string; field_of_study: string; start_year: number; end_year: number | null }[]
  preferences: { work_mode: string; relocation: string; distance: string | null } | null
}
export type OfferInput = {
  organization_id: string; title: string; description: string; contract_type: string; work_mode: string
  experience_level: string; governorate: string; city: string; min_salary: number | null
  max_salary: number | null; application_deadline: string | null; easy_apply: boolean
}
export type InterviewInput = {
  application_id: string; type: RecruiterInterview['type']; scheduled_at: string
  duration_minutes: number; location_or_url: string
}

const post = <T>(path: string, body: object) => request<T>(path, { method: 'POST', body: JSON.stringify(body) })
const patch = <T>(path: string, body: object) => request<T>(path, { method: 'PATCH', body: JSON.stringify(body) })

export const listOffers = (organizationId?: string) =>
  allPages<RecruiterOffer>(`/job-offers/?ordering=-created_at${organizationId ? `&organization_id=${organizationId}` : ''}`)
export const listApplications = () => allPages<RecruiterApplication>('/applications/')
export const listInterviews = () => allPages<RecruiterInterview>('/interviews/')
export const listSkills = () => allPages<SkillRef>('/skills/')
export const listOfferSkills = (offerId: string) => allPages<OfferSkill>(`/offer-skills/?offer_id=${offerId}`)
export const listStatusHistory = (applicationId: string) =>
  allPages<StatusHistory>(`/application-status-history/?application_id=${applicationId}`)
export const listEducationLevels = () => allPages<EducationLevel>('/education-levels/')
export const listCandidates = (query: string) => allPages<CandidateCard>(`/candidate-profiles/${query}`)
export const getCandidate = (id: string) => request<CandidateCard>(`/candidate-profiles/${id}/`)

export const createOffer = (data: OfferInput) => post<RecruiterOffer>('/job-offers/', data)
export const updateOffer = (id: string, data: Partial<OfferInput>) => patch<RecruiterOffer>(`/job-offers/${id}/`, data)
export const addOfferSkill = (offerId: string, skillId: string, mandatory: boolean) =>
  post('/offer-skills/', { offer_id: offerId, skill_id: skillId, is_mandatory: mandatory, importance: mandatory ? 'HIGH' : 'MEDIUM' })
export const updateOfferSkill = (id: string, mandatory: boolean) =>
  patch(`/offer-skills/${id}/`, { is_mandatory: mandatory, importance: mandatory ? 'HIGH' : 'MEDIUM' })
export const deleteOfferSkill = (id: string) => request<void>(`/offer-skills/${id}/`, { method: 'DELETE' })
export const transitionOffer = (id: string, status: RecruiterOffer['status']) =>
  post<RecruiterOffer>(`/job-offers/${id}/transition/`, { status })
export const transitionApplication = (id: string, status: string, reason?: string) =>
  post<RecruiterApplication>(`/applications/${id}/transition/`, { status, reason })
export const scheduleInterview = (data: InterviewInput) => post<RecruiterInterview>('/interviews/', data)
export const transitionInterview = (id: string, status: 'COMPLETED' | 'CANCELLED', feedback?: string) =>
  post<RecruiterInterview>(`/interviews/${id}/transition/`, { status, feedback })

export const applicantName = (applicant: Applicant) => `${applicant.first_name} ${applicant.last_name}`.trim() || 'Candidat'
export const candidateLabel = (a: RecruiterApplication) => applicantName(a.applicant)
