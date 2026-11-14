// Placement: frontend/src/lib/cvProposal.ts
// Brouillon de revue d’une analyse de CV : chaque ligne peut être cochée et corrigée.
// Seules les lignes cochées et complètes partent vers /cvs/{id}/apply-proposal/.

import type { CVProposal, CVProposalApply } from '../api/candidate.ts'

export type Row<T> = T & { include: boolean }
export type Draft = {
  experiences: Row<{ already: boolean; job_title: string; organization_name: string; start_date: string; end_date: string; description: string }>[]
  educations: Row<{ already: boolean; education_level: string; institution: string; field_of_study: string; start_year: string; end_year: string; description: string; degree: string }>[]
  skills: Row<{ name: string; category: string; level: string; isNew: boolean; already: boolean }>[]
  languages: Row<{ name: string; language_id: string; level: string; proficiency: string; already: boolean }>[]
  certifications: Row<{ already: boolean; name: string; certification_organization: string; issue_date: string; description: string }>[]
  projects: Row<{ already: boolean; name: string; description: string; repository_url: string; technologies: string }>[]
}
export type Section = keyof Draft

export const DEFAULT_SKILL_LEVEL = 'INTERMEDIATE'

/** Tout est coché par défaut, sauf ce qui est déjà dans le profil ou ne peut pas être ajouté. */
export function draftFromProposal(p: CVProposal): Draft {
  const text = (value: string | number | null | undefined) => (value == null ? '' : String(value))
  return {
    experiences: p.experiences.map((e) => ({ include: !e.already_on_profile, already: e.already_on_profile, job_title: e.job_title, organization_name: e.organization_name, start_date: text(e.start_date), end_date: text(e.end_date), description: e.description })),
    educations: p.educations.map((e) => ({ include: !e.already_on_profile, already: e.already_on_profile, education_level: text(e.education_level), institution: e.institution, field_of_study: e.field_of_study, start_year: text(e.start_year), end_year: text(e.end_year), description: e.description, degree: e.degree })),
    skills: p.skills.map((s) => ({ include: !s.already_on_profile, name: s.name, category: s.category, level: DEFAULT_SKILL_LEVEL, isNew: s.skill_id === null, already: s.already_on_profile })),
    languages: p.languages.map((l) => ({ include: !l.already_on_profile && l.language_id !== null, name: l.name, language_id: text(l.language_id), level: text(l.level), proficiency: l.proficiency, already: l.already_on_profile })),
    certifications: p.certifications.map((c) => ({ include: !c.already_on_profile, already: c.already_on_profile, name: c.name, certification_organization: c.certification_organization, issue_date: text(c.issue_date), description: c.description })),
    projects: p.projects.map((pr) => ({ include: !pr.already_on_profile, already: pr.already_on_profile, name: pr.name, description: pr.description, repository_url: pr.repository_url, technologies: pr.technologies.join(', ') })),
  }
}

const REQUIRED: { [K in Section]: (keyof Draft[K][number])[] } = {
  experiences: ['job_title', 'organization_name', 'start_date'],
  educations: ['education_level', 'institution', 'start_year'],
  skills: ['name', 'level'],
  languages: ['language_id', 'level'],
  certifications: ['name', 'certification_organization', 'issue_date'],
  projects: ['name'],
}

/** Champs obligatoires vides d’une ligne cochée (le formulaire les signale). */
export function missingFields<K extends Section>(section: K, row: Draft[K][number]): string[] {
  if (!row.include) return []
  return (REQUIRED[section] as string[]).filter((field) => !String((row as Record<string, unknown>)[field] ?? '').trim())
}

export function incompleteCount(draft: Draft): number {
  return (Object.keys(draft) as Section[]).reduce((total, section) =>
    total + (draft[section] as Draft[Section][number][]).filter((row) => missingFields(section, row).length > 0).length, 0)
}

export function selectedCount(draft: Draft): number {
  return (Object.keys(draft) as Section[]).reduce((total, section) => total + draft[section].filter((row) => row.include).length, 0)
}

const year = (value: string) => (value.trim() ? Number(value) : null)
const https = (value: string) => (value.trim().toLowerCase().startsWith('http') ? value.trim() : '')

/** Corps de la requête : uniquement les lignes cochées, aux formats attendus par l’API. */
export function applyPayload(draft: Draft): CVProposalApply {
  return {
    experiences: draft.experiences.filter((r) => r.include).map((r) => ({ job_title: r.job_title.trim(), organization_name: r.organization_name.trim(), start_date: r.start_date, end_date: r.end_date || null, description: r.description })),
    educations: draft.educations.filter((r) => r.include).map((r) => ({ education_level: r.education_level, institution: r.institution.trim(), field_of_study: r.field_of_study.trim(), start_year: Number(r.start_year), end_year: year(r.end_year), description: r.description })),
    skills: draft.skills.filter((r) => r.include).map((r) => ({ name: r.name.trim(), category: r.category, level: r.level })),
    languages: draft.languages.filter((r) => r.include).map((r) => ({ language_id: r.language_id, level: r.level })),
    certifications: draft.certifications.filter((r) => r.include).map((r) => ({ name: r.name.trim(), certification_organization: r.certification_organization.trim(), issue_date: r.issue_date, description: r.description })),
    projects: draft.projects.filter((r) => r.include).map((r) => ({ name: r.name.trim(), description: r.description, repository_url: https(r.repository_url), technologies: r.technologies.split(',').map((t) => t.trim()).filter(Boolean) })),
  }
}
