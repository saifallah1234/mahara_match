import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from 'react'
import { ApiError, setAccessToken, setSessionExpiredHandler } from '../api/client'
import * as authApi from '../api/auth'
import type { CurrentUser, Workspace } from '../api/auth'
import { isAssigned } from '../lib/authRouting'

type AuthStatus = 'loading' | 'guest' | 'authenticated' | 'error'

interface AuthValue {
  status: AuthStatus
  user: CurrentUser | null
  workspace: Workspace | null
  login: (email: string, password: string) => Promise<CurrentUser>
  logout: () => Promise<void>
  restore: () => Promise<void>
  refreshUser: () => Promise<void>
  selectWorkspace: (workspace: Workspace) => void
}

const AuthContext = createContext<AuthValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<AuthStatus>('loading')
  const [user, setUser] = useState<CurrentUser | null>(null)
  const [workspace, setWorkspace] = useState<Workspace | null>(null)

  const clear = useCallback(() => {
    setAccessToken(null)
    setUser(null)
    setWorkspace(null)
    setStatus('guest')
  }, [])

  const restore = useCallback(async () => {
    setStatus('loading')
    try {
      const current = await authApi.restore()
      setUser(current)
      setWorkspace(current.workspaces.length === 1 ? current.workspaces[0] : null)
      setStatus('authenticated')
    } catch (error) {
      if (error instanceof ApiError && error.status === 401) clear()
      else setStatus('error')
    }
  }, [clear])

  useEffect(() => {
    void restore()
    setSessionExpiredHandler(clear)
    return () => setSessionExpiredHandler(null)
  }, [clear, restore])

  const login = useCallback(async (email: string, password: string) => {
    try {
      const current = await authApi.login(email, password)
      setUser(current)
      setWorkspace(current.workspaces.length === 1 ? current.workspaces[0] : null)
      setStatus('authenticated')
      return current
    } catch (error) { clear(); throw error }
  }, [clear])

  const logout = useCallback(async () => {
    try { await authApi.logout() } finally { clear() }
  }, [clear])

  const selectWorkspace = useCallback((selection: Workspace) => {
    if (!user || !isAssigned(user.workspaces, selection)) return
    setWorkspace(selection)
  }, [user])

  const refreshUser = useCallback(async () => { setUser(await authApi.me()) }, [])

  const value = useMemo(() => ({ status, user, workspace, login, logout, restore, refreshUser, selectWorkspace }),
    [status, user, workspace, login, logout, restore, refreshUser, selectWorkspace])
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext)
  if (!value) throw new Error('AuthProvider is required.')
  return value
}
