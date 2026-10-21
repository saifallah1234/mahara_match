// Placement: frontend/tests/offerLifecycle.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { offerActions } from '../src/lib/offerLifecycle.ts'

// Mirrors _NEXT in backend/apps/recruitment/services/offer_lifecycle.py.
test('every backend offer transition is offered from its source status', () => {
  const targets = (status) => offerActions(status).map((action) => action.to)
  assert.deepEqual(targets('DRAFT'), ['PUBLISHED', 'ARCHIVED'])
  assert.deepEqual(targets('PUBLISHED'), ['PAUSED', 'CLOSED'])
  assert.deepEqual(targets('PAUSED'), ['PUBLISHED', 'CLOSED'])
  assert.deepEqual(targets('CLOSED'), ['ARCHIVED'])
  assert.deepEqual(targets('ARCHIVED'), [])
})

test('closing and archiving ask for confirmation, pausing and resuming do not', () => {
  const confirmed = (status) => offerActions(status).filter((action) => action.confirm).map((action) => action.to)
  assert.deepEqual(confirmed('DRAFT'), ['ARCHIVED'])
  assert.deepEqual(confirmed('PUBLISHED'), ['CLOSED'])
  assert.deepEqual(confirmed('PAUSED'), ['CLOSED'])
  assert.deepEqual(confirmed('CLOSED'), ['ARCHIVED'])
})
