// Placement: frontend/src/lib/candidateProfile.ts
import type { OwnedRecord, RecordKind } from '../api/candidate'

/** Profile sections in menu order. */
export const PROFILE_SECTIONS: RecordKind[] = ['experiences', 'educations', 'skills', 'certifications', 'projects', 'languages', 'preferences']

export const PROFILE_SECTION_LABEL: Record<RecordKind, string> = {
  experiences: 'Expériences', educations: 'Diplômes', skills: 'Compétences', certifications: 'Certifications',
  projects: 'Projets', languages: 'Langues', preferences: 'Préférences',
}

/** A display hint (sections filled out of sections available), not a stored score: Q26's formula stays open. */
export function profileCompleteness(records: Record<RecordKind, OwnedRecord[]>): { filled: number; total: number; next: RecordKind | null } {
  const empty = PROFILE_SECTIONS.filter((kind) => !records[kind].length)
  return { filled: PROFILE_SECTIONS.length - empty.length, total: PROFILE_SECTIONS.length, next: empty[0] ?? null }
}
