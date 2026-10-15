import assert from 'node:assert/strict'
import test from 'node:test'
import { isAssigned, loginPath, workspacePath } from '../src/lib/authRouting.ts'

const candidate = { role_code: 'CANDIDATE', organization: null }
const recruiter = { role_code: 'RECRUITER', organization: { id: 'org-a' } }
const secondRecruiter = { role_code: 'RECRUITER', organization: { id: 'org-b' } }

test('login routes zero, one and multiple workspaces', () => {
  assert.equal(loginPath([]), '/aucun-acces')
  assert.equal(loginPath([candidate]), '/candidat')
  assert.equal(loginPath([candidate, recruiter]), '/espaces')
})

test('a return URL is used only within the assigned workspace', () => {
  assert.equal(loginPath([candidate], '/candidat/profil'), '/candidat/profil')
  assert.equal(loginPath([candidate], '/admin'), '/candidat')
  assert.equal(workspacePath(recruiter, '/recruteur/offres'), '/recruteur/offres')
  assert.equal(workspacePath(recruiter, '/formation'), '/recruteur')
})

test('the selected organization must match a backend workspace', () => {
  assert.equal(isAssigned([candidate, recruiter], secondRecruiter), false)
  assert.equal(isAssigned([candidate, recruiter], recruiter), true)
})
