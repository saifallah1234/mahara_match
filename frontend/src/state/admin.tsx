import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from 'react'
import { useAuth } from './auth'
import * as api from '../api/admin'

type State = {
  users: api.AdminUser[]; organizations: api.AdminOrganization[]; loading: boolean; error: string | null
  setUserStatus: (id: string, status: api.AdminUser['status']) => Promise<void>
  verify: (id: string) => Promise<void>
  reject: (id: string) => Promise<void>
}
const Context = createContext<State | null>(null)

export function AdminProvider({ children }: { children: ReactNode }) {
  const auth = useAuth()
  const active = auth.status === 'authenticated' && auth.workspace?.role_code === 'ADMIN'
  const [users, setUsers] = useState<api.AdminUser[]>([])
  const [organizations, setOrganizations] = useState<api.AdminOrganization[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  const reload = useCallback(async () => {
    if (!active) return
    setLoading(true); setError(null)
    try {
      const [u, o] = await Promise.all([api.listUsers(), api.listOrganizations()])
      setUsers(u); setOrganizations(o)
    } catch (e) { setError(e instanceof Error ? e.message : 'Chargement impossible.') }
    finally { setLoading(false) }
  }, [active])
  useEffect(() => { void reload() }, [reload])

  const run = async (work: () => Promise<unknown>) => {
    setError(null)
    try { await work(); await reload() }
    catch (e) { setError(e instanceof Error ? e.message : 'Opération refusée.'); throw e }
  }
  const value: State = {
    users, organizations, loading, error,
    setUserStatus: (id, status) => run(() => api.setUserStatus(id, status)),
    verify: (id) => run(() => api.verifyOrganization(id)),
    reject: (id) => run(() => api.rejectOrganization(id)),
  }
  return <Context.Provider value={value}>{children}</Context.Provider>
}
export function useAdmin() {
  const v = useContext(Context)
  if (!v) throw new Error('AdminProvider is required.')
  return v
}