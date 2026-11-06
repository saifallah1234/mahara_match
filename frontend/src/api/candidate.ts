import { allPages } from './auth.ts'
import { request, requestBlob } from './client.ts'

export type Profile = { id: string; birth_date: string | null; country_code: string; governorate: string; city: string; headline: string; summary: string; employment_status: string; desired_job_title: string; availability_date: string | null; profile_visibility: 'PRIVATE' | 'RECRUITERS' | 'PUBLIC' }
export type OwnedRecord = { id: string; [key: string]: unknown }
export type Document = { id: string; file_name: string; size_bytes: number; uploaded_at: string }
export type CV = { id: string; document: string; title: string; language_code: string; is_primary: boolean; version_number: number }
export type Offer = { id: string; organization_id: string; organization_name: string; title: string; description: string; contract_type: string; work_mode: string; governorate: string; city: string; experience_level: string; min_salary: string | null; max_salary: string | null; application_deadline: string | null; published_at: string | null; status: string; easy_apply: boolean; offer_url: string; education_level_id: string | null }
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

export type ReviewRole = { id: string; label: string; version: string }
export type ReviewLevel = 'intern' | 'junior' | 'mid'
export type AtsIssue = { code: string; severity: 'high' | 'medium' | 'low'; component: string; message: string }
export type AtsBreakdown = { components: Record<string, number>; ats_readiness: number; role_fit: number; parse_degraded: boolean }
export type AtsAnalysis = { id: string; cv: string; overall_score: string; issues_json: AtsIssue[]; role_profile_id: string; role_profile_version: string; level: ReviewLevel; breakdown_json: AtsBreakdown; analyzed_at: string }
export const reviewRoles = () => request<ReviewRole[]>('/cv-review-roles/')
export const analyseCV = (cv: string, role_profile_id: string, level: ReviewLevel) =>
  save<AtsAnalysis>('/cv-analysis-results/', { cv, role_profile_id, level }, 'POST')
