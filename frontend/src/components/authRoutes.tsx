import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../state/auth'
import { ROLE_HOME } from '../lib/format'
import type { RoleCode } from '../lib/types'

export function ProtectedRoute() {
  const { status, user } = useAuth()
  const location = useLocation()
  if (status === 'loading') return <div className="p-8">Chargement de la session…</div>
  if (status === 'error') return <SessionError />
  if (status === 'guest') return <Navigate to="/connexion" replace state={{ from: location.pathname }} />
  if (!user?.workspaces.length && location.pathname !== '/aucun-acces') return <Navigate to="/aucun-acces" replace />
  return <Outlet />
}

function SessionError() {
  const { restore } = useAuth()
  return <main className="p-8"><p>La session n’a pas pu être chargée.</p>
    <button className="mt-3 text-teal" onClick={() => void restore()}>Réessayer</button></main>
}

export function RoleRoute({ role }: { role: RoleCode }) {
  const { user, workspace } = useAuth()
  if (!user?.workspaces.some((entry) => entry.role_code === role)) {
    return <Navigate to={user?.workspaces.length === 1 ? ROLE_HOME[user.workspaces[0].role_code] : '/espaces'} replace />
  }
  if (!workspace) return <Navigate to="/espaces" replace />
  if (workspace.role_code !== role) return <Navigate to={ROLE_HOME[workspace.role_code]} replace />
  return <Outlet />
}
