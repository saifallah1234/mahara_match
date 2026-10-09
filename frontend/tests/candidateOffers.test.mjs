import assert from 'node:assert/strict'
import test from 'node:test'
import { filterCandidateOffers } from '../src/lib/candidateOffers.ts'

test('contract and deposit mode filter all loaded offer pages', () => {
  const firstPage = [{ id: '1', contract_type: 'CDD', easy_apply: true }]
  const secondPage = [{ id: '2', contract_type: 'CDI', easy_apply: false }, { id: '3', contract_type: 'CDI', easy_apply: true }]
  assert.deepEqual(filterCandidateOffers([...firstPage, ...secondPage], 'CDI', 'platform').map((offer) => offer.id), ['3'])
  assert.deepEqual(filterCandidateOffers([...firstPage, ...secondPage], '', 'external').map((offer) => offer.id), ['2'])
})
