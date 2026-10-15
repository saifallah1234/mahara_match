import { useCallback, useEffect, useState } from 'react'
import { authPost, request } from '../api/client'
import { allPages } from '../api/auth'
import { PageBody, PageHeader } from '../components/layout'
import { ROLE_LABEL } from '../lib/format'
import type { RoleCode } from '../lib/types'

interface OnboardingRequest {
  id: string
  email: string
  first_name: string
  last_name: string
  requested_role: RoleCode
  organization_name: string
  matricule_fiscal: string
  status: string
}
interface Organization {
  id: string
  legal_name: string
  matricule_fiscal: string
  type: string
  verification_status: string
}

export default function AdminOnboarding() {
  const [requests, setRequests] = useState<OnboardingRequest[]>([])
  const [organizations, setOrganizations] = useState<Organization[]>([])
  const [busy, setBusy] = useState<string | null>(null)
  const [error, setError] = useState('')
  const load = useCallback(async () => {
    try {
      const [pending, orgs] = await Promise.all([
        allPages<OnboardingRequest>('/onboarding-requests/'), allPages<Organization>('/organizations/'),
      ])
      setRequests(pending.filter((entry) => entry.status === 'PENDING'))
      setOrganizations(orgs)
      setError('')
    } catch { setError('Impossible de charger les demandes.') }
  }, [])
  useEffect(() => { void load() }, [load])

  async function act(id: string, action: () => Promise<unknown>) {
    setBusy(id)
    setError('')
    try { await action(); await load() }
    catch { setError('Action refusée. Vérifiez l’organisation, le statut et vos droits.') }
    finally { setBusy(null) }
  }

  return <><PageHeader title="Demandes d’accès" description="Vérifier l’organisation avant d’activer un recruteur ou un responsable de formation." />
    <PageBody className="space-y-4">
      {error && <p role="alert" className="text-coral">{error}</p>}
      {requests.length === 0 && <p>Aucune demande en attente.</p>}
      {requests.map((entry) => {
        const org = organizations.find((candidate) => candidate.matricule_fiscal === entry.matricule_fiscal)
        const expectedType = entry.requested_role === 'RECRUITER' ? 'COMPANY' : 'TRAINING_PROVIDER'
        const compatible = org && (org.type === expectedType || (expectedType === 'COMPANY' && org.type === 'SUBSIDIARY'))
        return <section key={entry.id} className="rounded border border-line bg-white p-5">
          <h2 className="font-semibold">{entry.first_name} {entry.last_name} · {ROLE_LABEL[entry.requested_role]}</h2>
          <p className="text-sm text-slate">{entry.email} · {entry.organization_name} · {entry.matricule_fiscal}</p>
          {org ? <p className="mt-3 text-sm">Organisation correspondante : {org.legal_name} ({org.verification_status})</p>
            : <p className="mt-3 text-sm">Aucune organisation correspondante. Créez-la après vérification des pièces.</p>}
          <div className="mt-4 flex flex-wrap gap-3">
            {!org && <button className="rounded border border-teal px-3 py-2 text-teal disabled:opacity-50" disabled={busy === entry.id}
              onClick={() => void act(entry.id, () => request('/organizations/', { method: 'POST', body: JSON.stringify({
                type: expectedType, legal_name: entry.organization_name, matricule_fiscal: entry.matricule_fiscal,
              }) }))}>Créer l’organisation</button>}
            {org?.verification_status === 'PENDING' && compatible && <button className="rounded border border-teal px-3 py-2 text-teal disabled:opacity-50" disabled={busy === entry.id}
              onClick={() => void act(entry.id, () => authPost(`/organizations/${org.id}/verify/`))}>Marquer comme vérifiée</button>}
            <button className="rounded bg-teal px-3 py-2 text-white disabled:opacity-50" disabled={busy === entry.id || !compatible || org?.verification_status !== 'VERIFIED'}
              onClick={() => void act(entry.id, () => authPost(`/onboarding-requests/${entry.id}/approve/`, { organization_id: org?.id }))}>Approuver et activer</button>
            <button className="rounded border border-coral px-3 py-2 text-coral disabled:opacity-50" disabled={busy === entry.id}
              onClick={() => void act(entry.id, () => authPost(`/onboarding-requests/${entry.id}/reject/`))}>Rejeter</button>
          </div>
        </section>
      })}
    </PageBody>
  </>
}
