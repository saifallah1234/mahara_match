import assert from 'node:assert/strict'
import test from 'node:test'
import { filterCandidateOffers, matchBadge, shouldAutoCalculate } from '../src/lib/candidateOffers.ts'

test('contract and deposit mode filter all loaded offer pages', () => {
  const firstPage = [{ id: '1', contract_type: 'CDD', easy_apply: true }]
  const secondPage = [{ id: '2', contract_type: 'CDI', easy_apply: false }, { id: '3', contract_type: 'CDI', easy_apply: true }]
  assert.deepEqual(filterCandidateOffers([...firstPage, ...secondPage], 'CDI', 'platform').map((offer) => offer.id), ['3'])
  assert.deepEqual(filterCandidateOffers([...firstPage, ...secondPage], '', 'external').map((offer) => offer.id), ['2'])
})

test('the offer-card badge shows the rounded score and at most two missing skills', () => {
  const match = { offer_id: 'o', overall_score: '67.50', explanation_json: { matched_skills: ['sql'], missing_skills: ['docker', 'kubernetes', 'aws'] } }
  assert.deepEqual(matchBadge(match), { score: 68, missing: ['docker', 'kubernetes'] })
  assert.deepEqual(matchBadge({ ...match, explanation_json: null }), { score: 68, missing: [] })
})

test('the offer-card badge is empty without a score', () => {
  assert.equal(matchBadge(undefined), null)
  assert.equal(matchBadge({ offer_id: 'o', overall_score: null, explanation_json: { missing_skills: ['docker'] } }), null)
})

test('scores are calculated automatically once, for a candidate with skills and no fresh scores', () => {
  const base = { hasSkills: true, hasMatches: false, stale: false, alreadyTried: false }
  assert.equal(shouldAutoCalculate(base), true)
  assert.equal(shouldAutoCalculate({ ...base, hasMatches: true, stale: true }), true)
  assert.equal(shouldAutoCalculate({ ...base, hasMatches: true }), false)
  assert.equal(shouldAutoCalculate({ ...base, hasSkills: false }), false)
  assert.equal(shouldAutoCalculate({ ...base, alreadyTried: true }), false)
})
