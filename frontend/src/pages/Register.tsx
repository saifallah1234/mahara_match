import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { register, type Registration } from '../api/auth'
import { ApiError } from '../api/client'
import { AuthLayout } from '../components/AuthLayout'
import { Button, Field, Input, Note, Select } from '../components/ui'

export default function Register() {
  const [form, setForm] = useState<Registration>({
    email: '', password: '', first_name: '', last_name: '', account_type: 'CANDIDATE',
  })
  const [result, setResult] = useState<string | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const organization = form.account_type !== 'CANDIDATE'
  function set<K extends keyof Registration>(key: K, value: Registration[K]) {
    setForm((current) => ({ ...current, [key]: value }))
  }
  async function submit(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const response = await register(form)
      setResult(response.status)
    } catch (failure) {
      if (failure instanceof ApiError) {
        const firstDetail = failure.details && typeof failure.details === 'object'
          ? Object.values(failure.details)[0] : null
        setError(Array.isArray(firstDetail) && typeof firstDetail[0] === 'string'
          ? firstDetail[0] : failure.message)
      } else setError('Inscription impossible. Réessayez.')
    } finally { setBusy(false) }
  }
  return <AuthLayout title="Créer votre compte" description="Rejoignez Mahara Match et préparez la suite de votre parcours.">
    {result ? <div className="space-y-5">
      <div role="status"><Note tone={result === 'ACTIVE' ? 'info' : 'attention'}>{result === 'ACTIVE' ? 'Votre compte est prêt. Vous pouvez maintenant vous connecter.' : 'Votre demande a été enregistrée. Un administrateur doit vérifier votre organisation et activer votre compte.'}</Note></div>
      <Link className="inline-flex font-medium text-teal hover:underline" to="/connexion">Aller à la connexion →</Link>
    </div> : <form className="space-y-5" aria-busy={busy} onSubmit={(event) => void submit(event)}>
      <Field label="Vous souhaitez vous inscrire comme" hint={organization ? 'L’accès à votre organisation sera soumis à validation.' : 'Votre compte candidat sera disponible dès l’inscription.'}>
        <Select value={form.account_type} onChange={(event) => set('account_type', event.target.value as Registration['account_type'])}>
          <option value="CANDIDATE">Candidat</option><option value="RECRUITER">Recruteur</option><option value="TRAINING_MANAGER">Responsable de formation</option>
        </Select>
      </Field>
      <div className="grid gap-4 sm:grid-cols-2">
        <Field label="Prénom" required><Input autoComplete="given-name" placeholder="Votre prénom" required value={form.first_name} onChange={(event) => set('first_name', event.target.value)} /></Field>
        <Field label="Nom" required><Input autoComplete="family-name" placeholder="Votre nom" required value={form.last_name} onChange={(event) => set('last_name', event.target.value)} /></Field>
      </div>
      <Field label="Adresse e-mail" required><Input type="email" autoComplete="username" placeholder="vous@exemple.tn" required value={form.email} onChange={(event) => set('email', event.target.value)} /></Field>
      <Field label="Mot de passe" required hint="Au moins 8 caractères. Évitez les mots de passe courants ou uniquement numériques."><Input type="password" autoComplete="new-password" placeholder="Choisissez un mot de passe" required value={form.password} onChange={(event) => set('password', event.target.value)} /></Field>
      {organization && <fieldset className="space-y-4 border-t border-line pt-4">
        <legend className="px-1 text-sm font-semibold text-navy">Votre organisation</legend>
        <Note>Indiquez l’organisation existante ou proposée. Ces informations n’accordent aucun accès avant vérification.</Note>
        <Field label="Nom légal de l’organisation" required><Input autoComplete="organization" placeholder="Raison sociale" required value={form.organization_name ?? ''} onChange={(event) => set('organization_name', event.target.value)} /></Field>
        <Field label="Matricule fiscal" required hint="13 caractères : 7 chiffres, une lettre, puis 5 chiffres."><Input placeholder="1234567A12345" required maxLength={13} pattern="[0-9]{7}[A-Z][0-9]{5}" value={form.matricule_fiscal ?? ''} onChange={(event) => set('matricule_fiscal', event.target.value.toUpperCase())} /></Field>
      </fieldset>}
      {error && <div role="alert"><Note tone="danger">{error}</Note></div>}
      <Button type="submit" className="w-full py-3" disabled={busy}>{busy ? 'Enregistrement…' : organization ? 'Envoyer ma demande' : 'Créer mon compte'}</Button>
      <p className="border-t border-line pt-5 text-center text-sm text-slate">Déjà inscrit ? <Link className="font-medium text-teal hover:underline" to="/connexion">Se connecter</Link></p>
    </form>}
  </AuthLayout>
}
