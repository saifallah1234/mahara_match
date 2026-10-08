import { useState, type FormEvent } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { ApiError } from '../api/client'
import { AuthLayout } from '../components/AuthLayout'
import { Button, Field, Input, Note } from '../components/ui'
import { ROLE_HOME } from '../lib/format'
import { loginPath } from '../lib/authRouting'
import { useAuth } from '../state/auth'

export default function SignIn() {
  const { login, restore, status, user } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const from = (location.state as { from?: string } | null)?.from

  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const current = await login(email, password)
      navigate(loginPath(current.workspaces, from), { replace: true, state: { from } })
    } catch (failure) {
      setError(failure instanceof ApiError && failure.status === 401
        ? 'Identifiants incorrects ou compte inactif.' : 'Connexion impossible. Réessayez.')
    } finally { setBusy(false) }
  }

  return <AuthLayout title="Heureux de vous retrouver" description="Connectez-vous pour accéder à votre espace Mahara Match.">
    {status === 'authenticated' && user ? <>
      <Note>Vous êtes connecté avec {user.email}.</Note>
      <Link className="mt-5 inline-flex font-medium text-teal hover:underline" to={user.workspaces.length === 1 ? ROLE_HOME[user.workspaces[0].role_code] : '/espaces'}>Ouvrir mon espace →</Link>
    </> : status === 'loading' ? <p role="status" className="py-6 text-sm text-slate">Chargement de la session…</p>
      : status === 'error' ? <div className="space-y-4">
        <div role="alert"><Note tone="danger">Session indisponible. Réessayez dans quelques instants.</Note></div>
        <Button onClick={() => void restore()}>Réessayer</Button>
      </div> : <>
        <form className="space-y-5" aria-busy={busy} onSubmit={(event) => void submit(event)}>
          <Field label="Adresse e-mail" required>
            <Input type="email" autoComplete="username" placeholder="vous@exemple.tn" required value={email} onChange={(event) => setEmail(event.target.value)} />
          </Field>
          <Field label="Mot de passe" required>
            <Input type="password" autoComplete="current-password" placeholder="Votre mot de passe" required value={password} onChange={(event) => setPassword(event.target.value)} />
          </Field>
          {error && <div role="alert"><Note tone="danger">{error}</Note></div>}
          <Button type="submit" className="w-full py-3" disabled={busy}>{busy ? 'Connexion…' : 'Se connecter'}</Button>
        </form>
        <p className="mt-6 border-t border-line pt-5 text-center text-sm text-slate">Pas encore de compte ? <Link className="font-medium text-teal hover:underline" to="/inscription">Créer un compte</Link></p>
      </>}
  </AuthLayout>
}
