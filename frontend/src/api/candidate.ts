import { allPages } from './auth.ts'
import { request, requestBlob } from './client.ts'

export type Profile = { id: string; birth_date: string | null; country_code: string; governorate: string; city: string; headline: string; summary: string; employment_status: string; desired_job_title: string; availability_date: string | null; profile_visibility: 'PRIVATE' | 'RECRUITERS' | 'PUBLIC' }
export type OwnedRecord = { id: string; [key: string]: unknown }
export type Document = { id: string; file_name: string; size_bytes: number; uploaded_at: string }
export type CV = { id: string; document: string; title: string; language_code: string; is_primary: boolean; version_number: number; parse_status: '' | 'PROCESSING' | 'PARSED' | 'FAILED'; parsed_data_json: { error?: string } | null }
export type Offer = { id: string; organization_id: string; organization_name: string; company_name: string; title: string; description: string; contract_type: string; work_mode: string; governorate: string; city: string; experience_level: string; min_salary: string | null; max_salary: string | null; application_deadline: string | null; published_at: string | null; status: string; easy_apply: boolean; offer_url: string; education_level_id: string | null }
export type Application = { id: string; candidate_id: string; offer_id: string; offer_title: string; cv_id: string; status: string; cover_letter: string; applied_at: string; withdrawn_at: string | null }
export type Interview = { id: string; application_id: string; type: string; scheduled_at: string; duration_minutes: number; location_or_url: string; status: string }
export type History = { id: string; application_id: string; status: string; changed_at: string }
export type Program = { id: string; organization_id: string; organization_name: string; title: string; description: string; level: string; delivery_mode: string; status: string; is_free: boolean; price: string }
export type TrainingSession = { id: string; program: string; start_date: string; end_date: string; capacity: number; location_or_url: string; registration_deadline: string; status: string }
export type Enrollment = { id: string; session: string; candidate_id: string; program_title: string; session_start_date: string; status: string; enrolled_at: string; completion_rate: number }

export const records = {
  experiences: '/experiences/', educations: '/educations/', skills: '/candidate-skills/',
  languages: '/candidate-languages/', certifications: '/certifications/',
  projects: '/projects/', preferences: '/candidate-preferences/',
} as const
export type RecordKind = keyof typeof records
export const list = <T>(path: string) => allPages<T>(path)
export const save = <T>(path: string, data: object, method: 'POST' | 'PATCH' = 'PATCH') =>
  request<T>(path, { method, body: JSON.stringify(data) })
export const remove = (path: string) => request<void>(path, { method: 'DELETE' })
export const publishedOffers = (search = '', governorate = '') => list<Offer>(`/job-offers/?status=PUBLISHED${search ? `&search=${encodeURIComponent(search)}` : ''}${governorate ? `&governorate=${encodeURIComponent(governorate)}` : ''}`)
export async function uploadCV(file: File, title: string, documentId?: string): Promise<{ cv: CV; documentId: string }> {
  let id = documentId
  if (!id) {
    const form = new FormData()
    form.append('file', file)
    form.append('type', 'CV')
    id = (await request<Document>('/documents/', { method: 'POST', body: form })).id
  }
  try {
    return { cv: await save<CV>('/cvs/', { document: id, title }, 'POST'), documentId: id }
  } catch (error) {
    throw Object.assign(error instanceof Error ? error : new Error('Échec de création du CV.'), { documentId: id })
  }
}
export async function downloadPath(path: string, fileName: string) {
  const blob = await requestBlob(path)
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = fileName
  link.click()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}
export const download = (documentId: string, fileName: string) => downloadPath(`/documents/${documentId}/download/`, fileName)

// -- Analyse d’un CV : propositions à vérifier avant tout ajout au profil -----------
export type ProposedIdentity = { first_name: string; last_name: string; email: string; phone: string; country_code: string; governorate: string; city: string; headline: string; summary: string; linkedin: string; github: string }
export type ProposedExperience = { job_title: string; organization_name: string; start_date: string | null; end_date: string | null; description: string; already_on_profile: boolean }
export type ProposedEducation = { degree_level: string | null; degree: string; education_level: string | null; institution: string; field_of_study: string; start_year: number | null; end_year: number | null; description: string; already_on_profile: boolean }
export type ProposedSkill = { name: string; category: string; skill_id: string | null; already_on_profile: boolean }
export type ProposedLanguage = { name: string; code: string | null; proficiency: string; level: string | null; language_id: string | null; already_on_profile: boolean }
export type ProposedCertification = { name: string; certification_organization: string; issue_date: string | null; description: string; already_on_profile: boolean }
export type ProposedProject = { name: string; description: string; repository_url: string; technologies: string[]; already_on_profile: boolean }
export type CVProposal = {
  cv_id: string; provider: string; parsed_at: string | null; identity: ProposedIdentity
  experiences: ProposedExperience[]; educations: ProposedEducation[]; skills: ProposedSkill[]
  languages: ProposedLanguage[]; certifications: ProposedCertification[]; projects: ProposedProject[]
}
export type CVProposalApply = {
  experiences: { job_title: string; organization_name: string; start_date: string; end_date: string | null; description: string }[]
  educations: { education_level: string; institution: string; field_of_study: string; start_year: number; end_year: number | null; description: string }[]
  skills: { name: string; category: string; level: string }[]
  languages: { language_id: string; level: string }[]
  certifications: { name: string; certification_organization: string; issue_date: string; description: string }[]
  projects: { name: string; description: string; repository_url: string; technologies: string[] }[]
}
export const getCV = (id: string) => request<CV>(`/cvs/${id}/`)
export const parseCV = (id: string) => request<CV>(`/cvs/${id}/parse/`, { method: 'POST' })
export const cvProposal = (id: string) => request<CVProposal>(`/cvs/${id}/profile-proposal/`)
export const applyCVProposal = (id: string, body: CVProposalApply) =>
  request<Record<string, number>>(`/cvs/${id}/apply-proposal/`, { method: 'POST', body: JSON.stringify(body) })
