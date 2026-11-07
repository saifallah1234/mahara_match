// Placement: frontend/tests/auditSummary.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { auditSummary } from '../src/lib/auditSummary.ts'

const users = [{ id: 'u1', first_name: 'Amel', last_name: 'Ben Salah' }]
const organizations = [{ id: 'o1', legal_name: 'Tunisie Formation' }]
const log = (over) => ({ actor_user_id: null, actor_type: 'USER', entity_type: 'training_program', entity_id: 'p1', ...over })

test('the actor is named from the admin account list', () => {
  assert.equal(auditSummary(log({ actor_user_id: 'u1' }), users, organizations).actor, 'Amel Ben Salah')
})

test('without a known account the actor kind is shown, and "Système" when there is none', () => {
  assert.equal(auditSummary(log({ actor_type: 'SYSTEM' }), users, organizations).actor, 'Système')
  assert.equal(auditSummary(log({ actor_user_id: 'gone' }), users, organizations).actor, 'Utilisateur')
  assert.equal(auditSummary(log({ actor_type: 'ANETI_AGENT' }), users, organizations).actor, 'Agent ANETI')
})

test('the record names the account or organization concerned, otherwise its type', () => {
  assert.equal(auditSummary(log({ entity_type: 'user', entity_id: 'u1' }), users, organizations).record, 'Compte « Amel Ben Salah »')
  assert.equal(auditSummary(log({ entity_type: 'organization', entity_id: 'o1' }), users, organizations).record, 'Organisation « Tunisie Formation »')
  assert.equal(auditSummary(log({}), users, organizations).record, 'Programme')
  assert.equal(auditSummary(log({ entity_type: 'mystery' }), users, organizations).record, 'Autre entité')
})
