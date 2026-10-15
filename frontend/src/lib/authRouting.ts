import { ROLE_HOME } from './format.ts'
import type { Workspace } from '../api/auth'

export function workspacePath(workspace: Workspace, from?: string): string {
  const home = ROLE_HOME[workspace.role_code]
  return from && (from === home || from.startsWith(`${home}/`)) ? from : home
}

export function loginPath(workspaces: Workspace[], from?: string): string {
  if (workspaces.length === 0) return '/aucun-acces'
  if (workspaces.length > 1) return '/espaces'
  return workspacePath(workspaces[0], from)
}

export function isAssigned(workspaces: Workspace[], choice: Workspace): boolean {
  return workspaces.some((available) =>
    available.role_code === choice.role_code && available.organization?.id === choice.organization?.id
  )
}
