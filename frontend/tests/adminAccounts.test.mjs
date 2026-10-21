// Placement: frontend/tests/adminAccounts.test.mjs
import assert from 'node:assert/strict'
import test from 'node:test'
import { runAccountCreation } from '../src/lib/adminAccounts.ts'

const draft = { email: 'ministere@example.tn', first_name: 'Amel', last_name: 'Ben Salah', password: 'x', role_id: 'r1', organization_id: null }

const staffDraft = { ...draft, organization_id: 'org1' }

function recordingApi(failAt = null) {
  const calls = []
  const step = (name, result) => async (...args) => {
    calls.push(name)
    if (failAt === name) throw new Error(`${name} refused`)
    return result ?? args
  }
  return {
    calls,
    api: {
      createUser: step('createUser', { id: 'u1' }),
      joinOrganization: step('joinOrganization'),
      assignRole: step('assignRole'),
      activate: step('activate'),
    },
  }
}

const fresh = { userId: null, joined: false, roleAssigned: false, activated: false }

test('an account is created, given its role, then activated, in that order', async () => {
  const { api, calls } = recordingApi()
  const progress = await runAccountCreation(draft, fresh, api)
  assert.deepEqual(calls, ['createUser', 'assignRole', 'activate'])
  assert.deepEqual(progress, { userId: 'u1', joined: false, roleAssigned: true, activated: true })
})

test('an organization role joins the organization before the role is assigned', async () => {
  const { api, calls } = recordingApi()
  await runAccountCreation(staffDraft, fresh, api)
  assert.deepEqual(calls, ['createUser', 'joinOrganization', 'assignRole', 'activate'])
})

test('a failed role step keeps the created account and names the step to retry', async () => {
  const { api } = recordingApi('assignRole')
  await assert.rejects(
    runAccountCreation(draft, fresh, api),
    (error) => error.step === 'assignRole' && error.progress.userId === 'u1' && !error.progress.roleAssigned,
  )
})

test('a failed membership keeps the account and retries from the membership step', async () => {
  const failing = recordingApi('joinOrganization')
  await assert.rejects(runAccountCreation(staffDraft, fresh, failing.api), (error) => error.step === 'joinOrganization' && !error.progress.joined)
  const retry = recordingApi()
  const progress = await runAccountCreation(staffDraft, { ...fresh, userId: 'u1' }, retry.api)
  assert.deepEqual(retry.calls, ['joinOrganization', 'assignRole', 'activate'])
  assert.equal(progress.activated, true)
})

test('a retry resumes after the completed steps and does not create the account twice', async () => {
  const { api, calls } = recordingApi()
  const progress = await runAccountCreation(draft, { ...fresh, userId: 'u1', roleAssigned: true }, api)
  assert.deepEqual(calls, ['activate'])
  assert.equal(progress.activated, true)
})
