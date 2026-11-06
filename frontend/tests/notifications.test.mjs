// Placement: frontend/tests/notifications.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { notificationPath } from '../src/lib/notifications.ts'

test('a notification opens the page where its change can be seen, per role', () => {
  assert.equal(notificationPath('recruitment.application.submitted', 'RECRUITER'), '/recruteur/candidatures')
  assert.equal(notificationPath('recruitment.application.status_changed', 'CANDIDATE'), '/candidat/candidatures')
  assert.equal(notificationPath('training.enrollment.created', 'TRAINING_MANAGER'), '/formation/sessions')
  assert.equal(notificationPath('training.enrollment.status_changed', 'CANDIDATE'), '/candidat/formations')
})

test('an unknown or onboarding notification falls back to the role home page', () => {
  assert.equal(notificationPath('identity.onboarding.approved', 'RECRUITER'), '/recruteur')
  assert.equal(notificationPath('something.new', 'ADMIN'), '/admin')
})
