// Placement: frontend/src/pages/admin/AccountDialogs.tsx
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Button, ConfirmDialog, Field, Input, Modal, Select, Table, Row, Cell } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import * as api from '../../api/admin'
import { runAccountCreation, type AccountDraft, type AccountProgress, type AccountSteps } from '../../lib/adminAccounts'
import { ADMIN_CREATABLE_ROLES, organizationsForRole, roleNeedsOrganization } from '../../lib/adminFilters'
import { ROLE_LABEL, labelFor } from '../../lib/format'
import { addMember, listMembers } from '../../api/organization'

const STEP_LABEL: Record<string, string> = {
  createUser: 'la création du compte', joinOrganization: 'l’ajout à l’organisation',
  assignRole: 'l’attribution du rôle', activate: 'l’activation du compte',
}
const joinAsMember = (organizationId: string, userId: string) => addMember(organizationId, { user: userId, job_title: '', joined_at: null })
const accountSteps: AccountSteps = {
  createUser: (d) => api.createUser({ email: d.email, password: d.password, first_name: d.first_name, last_name: d.last_name }),
  joinOrganization: (userId, d) => joinAsMember(String(d.organization_id), userId),
  assignRole: (userId, d) => api.assignRole({ user_id: userId, role_id: d.role_id, organization_id: d.organization_id }),
  activate: (userId) => api.setUserStatus(userId, 'ACTIVE'),
}
const EMPTY_FORM = { email: '', first_name: '', last_name: '', password: '', role_code: 'RECRUITER', organization_id: '' }

/** Crée le compte en trois appels. Si une étape échoue, le compte déjà créé reste et « Reprendre » relance l’étape. */
export function CreateAccountDialog({ onClose }: { onClose: () => void }) {
  const { roles, organizations, reload } = useAdmin()
  const [form, setForm] = useState(EMPTY_FORM)
  const [resume, setResume] = useState<{ draft: AccountDraft; progress: AccountProgress } | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })
  const setRole = (e: { target: { value: string } }) => setForm({ ...form, role_code: e.target.value, organization_id: '' })
  const needsOrganization = roleNeedsOrganization(form.role_code)
  const choices = organizationsForRole(organizations, form.role_code)
  const complete = form.email.trim() && form.first_name.trim() && form.last_name.trim() && form.password && (!needsOrganization || form.organization_id)

  async function submit(draft: AccountDraft, progress: AccountProgress) {
    setBusy(true); setMessage(null)
    try {
      await runAccountCreation(draft, progress, accountSteps)
      await reload()
      onClose()
    } catch (error) {
      const failure = error as Error & { step?: string; progress?: AccountProgress }
      const created = failure.progress?.userId ? 'Le compte est créé, mais ' : ''
      setResume({ draft, progress: failure.progress ?? progress })
      setMessage(`${created}l’étape « ${STEP_LABEL[failure.step ?? 'createUser']} » a échoué : ${failure.message}`)
      await reload()
    } finally { setBusy(false) }
  }

  function start() {
    const role = roles.find((r) => r.code === form.role_code)
    if (!role) { setMessage('Rôle introuvable. Rechargez la page.'); return }
    const draft: AccountDraft = {
      email: form.email.trim(), first_name: form.first_name.trim(), last_name: form.last_name.trim(), password: form.password,
      role_id: role.id, organization_id: needsOrganization ? form.organization_id : null,
    }
    void submit(draft, { userId: null, joined: false, roleAssigned: false, activated: false })
  }

  return (
    <Modal
      open
      onClose={onClose}
      title="Créer un compte"
      footer={
        <>
          <Button variant="secondaire" onClick={onClose}>Annuler</Button>
          {resume
            ? <Button disabled={busy} onClick={() => void submit(resume.draft, resume.progress)}>Reprendre</Button>
            : <Button disabled={!complete || busy} onClick={start}>Créer le compte</Button>}
        </>
      }
    >
      <div className="space-y-4">
        {message && <p role="alert" className="text-[13px] text-coral">{message}</p>}
        <div className="grid gap-4 sm:grid-cols-2">
          <Field label="Prénom" required><Input value={form.first_name} onChange={set('first_name')} disabled={!!resume} /></Field>
          <Field label="Nom" required><Input value={form.last_name} onChange={set('last_name')} disabled={!!resume} /></Field>
          <div className="sm:col-span-2"><Field label="Adresse e-mail" required><Input type="email" value={form.email} onChange={set('email')} disabled={!!resume} /></Field></div>
          <div className="sm:col-span-2">
            <Field label="Mot de passe temporaire" required hint="Remettez-le à la personne hors de l’application. Aucune invitation n’est envoyée.">
              <Input type="password" value={form.password} onChange={set('password')} disabled={!!resume} />
            </Field>
          </div>
          <Field label="Rôle" required>
            <Select value={form.role_code} onChange={setRole} disabled={!!resume}>
              {ADMIN_CREATABLE_ROLES.map((code) => <option key={code} value={code}>{labelFor(ROLE_LABEL, code)}</option>)}
            </Select>
          </Field>
          {needsOrganization && (
            <Field label="Organisation" required>
              <Select value={form.organization_id} onChange={set('organization_id')} disabled={!!resume}>
                <option value="">Choisir…</option>
                {choices.map((o) => <option key={o.id} value={o.id}>{o.legal_name}</option>)}
              </Select>
              {choices.length === 0 && <span className="mt-1 block text-[12px] text-coral">Aucune organisation de ce type.</span>}
            </Field>
          )}
        </div>
      </div>
    </Modal>
  )
}

/** Rôles d’un compte : retrait avec confirmation, ajout d’un rôle. */
export function AccountDetailDialog({ userId, onClose }: { userId: string; onClose: () => void }) {
  const { users, roles, userRoles, organizations, addRole, removeRole } = useAdmin()
  const user = users.find((u) => u.id === userId)
  const [roleCode, setRoleCode] = useState('RECRUITER')
  const [organizationId, setOrganizationId] = useState('')
  const [removing, setRemoving] = useState<api.UserRole | null>(null)
  const [error, setError] = useState<string | null>(null)
  if (!user) return null

  const assignments = userRoles.filter((r) => r.user_id === user.id)
  const orgName = (id: string | null) => (id ? organizations.find((o) => o.id === id)?.legal_name ?? 'Organisation inconnue' : 'Global')
  const needsOrganization = roleNeedsOrganization(roleCode)
  const choices = organizationsForRole(organizations, roleCode)

  // Le rôle d’organisation n’est accepté que pour un membre : on rejoint l’organisation d’abord si besoin.
  async function add(roleId: string) {
    setError(null)
    try {
      if (needsOrganization) {
        const members = await listMembers(organizationId)
        if (!members.some((m) => m.user === user!.id)) await joinAsMember(organizationId, user!.id)
      }
      await addRole({ user_id: user!.id, role_id: roleId, organization_id: needsOrganization ? organizationId : null })
    } catch (e) { setError(e instanceof Error ? e.message : 'Ajout refusé.') }
  }

  return (
    <Modal open onClose={onClose} title={`${user.first_name} ${user.last_name}`}>
      <div className="space-y-5">
        <p className="text-[13px] text-slate">{user.email}</p>
        {error && <p role="alert" className="text-[13px] text-coral">{error}</p>}
        <Table head={['Rôle', 'Organisation', '']}>
          {assignments.map((a) => (
            <Row key={a.id}>
              <Cell className="text-[13px]">{labelFor(ROLE_LABEL, a.role_code, 'Autre rôle')}</Cell>
              <Cell className="text-[13px] text-slate">{orgName(a.organization_id)}</Cell>
              <Cell className="text-right"><Button size="sm" variant="danger" onClick={() => setRemoving(a)}>Retirer</Button></Cell>
            </Row>
          ))}
        </Table>
        {assignments.length === 0 && <p className="text-[13px] text-slate">Aucun rôle attribué.</p>}
        <div className="grid gap-3 sm:grid-cols-[1fr_1fr_auto] sm:items-end">
          <Field label="Ajouter un rôle">
            <Select value={roleCode} onChange={(e) => { setRoleCode(e.target.value); setOrganizationId('') }}>
              {ADMIN_CREATABLE_ROLES.map((code) => <option key={code} value={code}>{labelFor(ROLE_LABEL, code)}</option>)}
            </Select>
          </Field>
          {needsOrganization ? (
            <Field label="Organisation">
              <Select value={organizationId} onChange={(e) => setOrganizationId(e.target.value)}>
                <option value="">Choisir…</option>
                {choices.map((o) => <option key={o.id} value={o.id}>{o.legal_name}</option>)}
              </Select>
            </Field>
          ) : <span />}
          <Button
            disabled={needsOrganization && !organizationId}
            onClick={() => { const role = roles.find((r) => r.code === roleCode); if (role) void add(role.id) }}
          >
            Ajouter
          </Button>
        </div>
        <p className="text-[12px] text-slate">Un rôle d’organisation ajoute aussi le compte comme membre de cette organisation.</p>
        {user.status === 'PENDING' && <p className="text-[13px]"><Link to="/admin/demandes" className="font-medium text-teal hover:underline">Voir la demande d’accès</Link></p>}
      </div>
      {removing && (
        <ConfirmDialog
          title="Retirer ce rôle ?"
          danger
          onCancel={() => setRemoving(null)}
          onConfirm={() => { void removeRole(removing.id).catch(() => {}); setRemoving(null) }}
        >
          Le rôle {labelFor(ROLE_LABEL, removing.role_code, 'Autre rôle')} sera retiré à {user.first_name} {user.last_name}.
        </ConfirmDialog>
      )}
    </Modal>
  )
}
