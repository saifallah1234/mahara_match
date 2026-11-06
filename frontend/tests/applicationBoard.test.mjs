// Placement: frontend/tests/applicationBoard.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { laterStages } from '../src/lib/statusMachine.ts'

test('a recruiter can move an application to any later stage, not only the next one', () => {
  assert.deepEqual(laterStages('SUBMITTED'), ['UNDER_REVIEW', 'PRESELECTED', 'INTERVIEW', 'OFFERED', 'HIRED'])
  assert.deepEqual(laterStages('INTERVIEW'), ['OFFERED', 'HIRED'])
})

test('final, rejected and withdrawn applications have no forward stage', () => {
  assert.deepEqual(laterStages('HIRED'), [])
  assert.deepEqual(laterStages('REJECTED'), [])
  assert.deepEqual(laterStages('WITHDRAWN'), [])
})
