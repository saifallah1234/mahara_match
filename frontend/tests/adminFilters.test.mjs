// Placement: frontend/tests/adminFilters.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { ADMIN_CREATABLE_ROLES, filterOrganizations, filterUsers, organizationsForRole, roleNeedsOrganization } from '../src/lib/adminFilters.ts'
import { ROLE_LABEL } from '../src/lib/format.ts'

const users = [
  { id: 'a', first_name: 'Amel', last_name: 'Ben Salah', email: 'amel@aneti.tn', role_assignments: [{ role_code: 'MINISTRY_MANAGER', organization_id: null }] },
  { id: 'b', first_name: 'Karim', last_name: 'Trabelsi', email: 'karim@company.tn', role_assignments: [{ role_code: 'RECRUITER', organization_id: 'o1' }, { role_code: 'ANETI_AGENT', organization_id: null }] },
]

test('the account search matches first name, last name and e-mail, ignoring case', () => {
  assert.deepEqual(filterUsers(users, { q: 'SALAH', role: '' }).map((u) => u.id), ['a'])
  assert.deepEqual(filterUsers(users, { q: 'company', role: '' }).map((u) => u.id), ['b'])
  assert.deepEqual(filterUsers(users, { q: 'karim trab', role: '' }).map((u) => u.id), ['b'])
})

test('the role filter keeps users holding that role, and an empty role keeps everyone', () => {
  assert.deepEqual(filterUsers(users, { q: '', role: 'RECRUITER' }).map((u) => u.id), ['b'])
  assert.equal(filterUsers(users, { q: '', role: '' }).length, 2)
})

test('the role filter does not offer the ANETI agent, which is not a human role', () => {
  assert.equal('ANETI_AGENT' in ROLE_LABEL, false)
})

test('admins create only human staff roles; organization roles need an organization of the matching type', () => {
  assert.deepEqual(ADMIN_CREATABLE_ROLES, ['RECRUITER', 'TRAINING_MANAGER', 'MINISTRY_MANAGER', 'ADMIN'])
  assert.equal(roleNeedsOrganization('RECRUITER'), true)
  assert.equal(roleNeedsOrganization('TRAINING_MANAGER'), true)
  assert.equal(roleNeedsOrganization('MINISTRY_MANAGER'), true)
  assert.equal(roleNeedsOrganization('ADMIN'), false)
  const mixed = [
    { id: 'c', type: 'COMPANY', verification_status: 'VERIFIED' }, { id: 's', type: 'SUBSIDIARY', verification_status: 'VERIFIED' },
    { id: 't', type: 'TRAINING_PROVIDER', verification_status: 'VERIFIED' }, { id: 'm', type: 'MINISTRY', verification_status: 'VERIFIED' },
    { id: 'p', type: 'MINISTRY', verification_status: 'PENDING' },
  ]
  assert.deepEqual(organizationsForRole(mixed, 'RECRUITER').map((o) => o.id), ['c', 's'])
  assert.deepEqual(organizationsForRole(mixed, 'TRAINING_MANAGER').map((o) => o.id), ['t'])
  assert.deepEqual(organizationsForRole(mixed, 'MINISTRY_MANAGER').map((o) => o.id), ['m'], 'a pending ministry gives no permissions')
})

const orgs = [
  { id: 'o1', type: 'COMPANY', verification_status: 'PENDING' },
  { id: 'o2', type: 'TRAINING_PROVIDER', verification_status: 'VERIFIED' },
  { id: 'o3', type: 'COMPANY', verification_status: 'VERIFIED' },
]

test('organization filters combine status and type', () => {
  assert.deepEqual(filterOrganizations(orgs, { status: '', type: '' }).map((o) => o.id), ['o1', 'o2', 'o3'])
  assert.deepEqual(filterOrganizations(orgs, { status: 'VERIFIED', type: 'COMPANY' }).map((o) => o.id), ['o3'])
  assert.deepEqual(filterOrganizations(orgs, { status: 'PENDING', type: '' }).map((o) => o.id), ['o1'])
})
