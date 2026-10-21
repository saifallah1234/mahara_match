// Placement: frontend/tests/citations.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { citationPath } from '../src/lib/citations.ts'

test('an offer citation opens the offer in the viewer’s own workspace', () => {
  assert.equal(citationPath('offer:o1', 'RECRUITER'), '/recruteur/offres/o1')
  assert.equal(citationPath('offer:o1', 'CANDIDATE'), '/candidat/offres/o1')
})

test('a candidate profile citation opens the recruiter discovery detail', () => {
  assert.equal(citationPath('candidate_profile:c1', 'RECRUITER'), '/recruteur/candidats/c1')
})

test('training programs and malformed references have no link', () => {
  assert.equal(citationPath('program:p1', 'CANDIDATE'), null)
  assert.equal(citationPath('offer', 'RECRUITER'), null)
})
