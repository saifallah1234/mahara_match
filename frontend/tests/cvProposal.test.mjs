// Placement: frontend/tests/cvProposal.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { applyPayload, draftFromProposal, incompleteCount, missingFields, selectedCount } from '../src/lib/cvProposal.ts'

const proposal = {
  cv_id: 'cv-1', provider: 'ollama:qwen2.5:7b', parsed_at: null,
  identity: { first_name: 'Yasmine', last_name: 'Chakroun', email: '', phone: '', country_code: 'TN', governorate: 'Ariana', city: 'Ariana', headline: '', summary: '', linkedin: '', github: '' },
  experiences: [
    { job_title: 'Stagiaire', organization_name: 'OneTech', start_date: '2025-07-01', end_date: null, description: '- Migration Odoo', already_on_profile: false },
    { job_title: 'Développeuse', organization_name: 'Acme', start_date: null, end_date: null, description: '', already_on_profile: false },
  ],
  educations: [{ degree_level: 'master', degree: "Diplôme d'Ingénieur", education_level: 'lvl-5', institution: 'FSB', field_of_study: 'Génie Logiciel', start_year: 2024, end_year: null, description: '', already_on_profile: false }],
  skills: [
    { name: 'Python', category: 'programming_language', skill_id: 'sk-1', already_on_profile: true },
    { name: 'Odoo', category: 'technical', skill_id: null, already_on_profile: false },
  ],
  languages: [
    { name: 'Français', code: 'fr', proficiency: 'Courant', level: 'C1', language_id: 'fr-id', already_on_profile: false },
    { name: 'Espagnol', code: 'es', proficiency: 'Notions', level: 'A2', language_id: null, already_on_profile: false },
  ],
  certifications: [],
  projects: [{ name: 'Mahara', description: 'Plateforme', repository_url: 'github.com/x', technologies: ['Django', 'React'], already_on_profile: true }],
}

test('everything addable is checked; what is on the profile or unknown is not', () => {
  const draft = draftFromProposal(proposal)
  assert.deepEqual(draft.skills.map((s) => [s.name, s.include, s.isNew]), [['Python', false, false], ['Odoo', true, true]])
  assert.deepEqual(draft.languages.map((l) => l.include), [true, false])
  assert.equal(draft.projects[0].include, false) // already on the profile
  assert.equal(selectedCount(draft), 5)
})

test('a checked row without its required fields blocks the submission until fixed or unchecked', () => {
  const draft = draftFromProposal(proposal)
  assert.deepEqual(missingFields('experiences', draft.experiences[1]), ['start_date'])
  assert.equal(incompleteCount(draft), 1)
  draft.experiences[1].include = false
  assert.equal(incompleteCount(draft), 0)
})

test('only checked rows are sent, in the API formats', () => {
  const draft = draftFromProposal(proposal)
  draft.experiences[1].include = false
  draft.projects[0].include = true
  const body = applyPayload(draft)
  assert.equal(body.experiences.length, 1)
  assert.deepEqual(body.educations[0], { education_level: 'lvl-5', institution: 'FSB', field_of_study: 'Génie Logiciel', start_year: 2024, end_year: null, description: '' })
  assert.deepEqual(body.skills, [{ name: 'Odoo', category: 'technical', level: 'INTERMEDIATE' }])
  assert.deepEqual(body.languages, [{ language_id: 'fr-id', level: 'C1' }])
  assert.deepEqual(body.projects[0], { name: 'Mahara', description: 'Plateforme', repository_url: '', technologies: ['Django', 'React'] })
})
