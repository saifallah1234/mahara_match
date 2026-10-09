import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { ROLE_HOME, ROLE_LABEL } from '../lib/format'
import { workspacePath } from '../lib/authRouting'
import { useAuth } from '../state/auth'

export function Workspaces() {
  const { user, workspace, selectWorkspace } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const from = (location.state as { from?: string } | null)?.from
  if (!user?.workspaces.length) return <NoAccess />
  return <main className="mx-auto max-w-xl p-8">
    <h1 className="text-2xl font-semibold">Choisir un espace</h1>
    <p className="mt-2 text-slate">Espaces autorisés pour {user.email}</p>
    <ul className="mt-6 space-y-3">{user.workspaces.map((entry) => <li key={`${entry.role_code}:${entry.organization?.id ?? ''}`}>
      <button className="w-full rounded border border-line p-4 text-left hover:border-teal" onClick={() => {
        selectWorkspace(entry)
        navigate(workspacePath(entry, from), { replace: true })
      }}>
        <span className="block font-medium">{ROLE_LABEL[entry.role_code]}</span>
        {entry.organization && <span className="block text-sm text-slate">{entry.organization.legal_name}</span>}
      </button>
    </li>)}</ul>
    {workspace && <Link className="mt-6 inline-block text-teal" to={ROLE_HOME[workspace.role_code]}>Retour à mon espace</Link>}
  </main>
}

export function NoAccess() {
  const { logout, user } = useAuth()
  const navigate = useNavigate()
  if (user?.workspaces.length) return <Navigate to={user.workspaces.length === 1 ? ROLE_HOME[user.workspaces[0].role_code] : '/espaces'} replace />
  return <main className="mx-auto max-w-xl p-8">
    <h1 className="text-2xl font-semibold">Aucun espace disponible</h1>
    <p className="mt-2 text-slate">Aucun rôle actif ne permet d’ouvrir un tableau de bord. Contactez l’administration si votre accès vient d’être approuvé.</p>
    <button className="mt-5 text-teal" onClick={() => void logout().catch(() => {}).finally(() => navigate('/connexion'))}>Se déconnecter</button>
  </main>
}
