// Placement: frontend/src/lib/adminAccounts.ts

export type AccountProgress = { userId: string | null; joined: boolean; roleAssigned: boolean; activated: boolean }
export type AccountDraft = {
  email: string; first_name: string; last_name: string; password: string
  role_id: string; organization_id: string | null
}
export type AccountSteps = {
  createUser: (draft: AccountDraft) => Promise<{ id: string }>
  joinOrganization: (userId: string, draft: AccountDraft) => Promise<unknown>
  assignRole: (userId: string, draft: AccountDraft) => Promise<unknown>
  activate: (userId: string) => Promise<unknown>
}

/**
 * Lance les étapes de création qui ne sont pas encore faites. Le backend n’attribue un rôle d’organisation
 * qu’à un membre : le compte rejoint donc l’organisation d’abord. Un échec porte le nom de l’étape et l’avancement.
 */
export async function runAccountCreation(draft: AccountDraft, start: AccountProgress, api: AccountSteps): Promise<AccountProgress> {
  const progress = { ...start }
  let step = 'createUser'
  try {
    if (!progress.userId) progress.userId = (await api.createUser(draft)).id
    if (draft.organization_id && !progress.joined) {
      step = 'joinOrganization'
      await api.joinOrganization(progress.userId, draft)
      progress.joined = true
    }
    step = 'assignRole'
    if (!progress.roleAssigned) { await api.assignRole(progress.userId, draft); progress.roleAssigned = true }
    step = 'activate'
    if (!progress.activated) { await api.activate(progress.userId); progress.activated = true }
    return progress
  } catch (cause) {
    throw Object.assign(cause instanceof Error ? cause : new Error(String(cause)), { step, progress })
  }
}
