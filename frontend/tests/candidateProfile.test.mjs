// Placement: frontend/tests/candidateProfile.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { profileCompleteness } from '../src/lib/candidateProfile.ts'

const records = (filled) => Object.fromEntries(
  ['experiences', 'educations', 'skills', 'certifications', 'projects', 'languages', 'preferences']
    .map((kind) => [kind, filled.includes(kind) ? [{ id: kind }] : []]),
)

test('completeness counts filled sections and points to the first empty one in menu order', () => {
  assert.deepEqual(profileCompleteness(records(['experiences', 'skills', 'languages'])), { filled: 3, total: 7, next: 'educations' })
})

test('an empty profile starts with experiences, a full profile has no next section', () => {
  assert.deepEqual(profileCompleteness(records([])), { filled: 0, total: 7, next: 'experiences' })
  assert.deepEqual(profileCompleteness(records(['experiences', 'educations', 'skills', 'certifications', 'projects', 'languages', 'preferences'])), { filled: 7, total: 7, next: null })
})
