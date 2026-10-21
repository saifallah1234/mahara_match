// Placement: frontend/src/pages/admin/OrganisationDetail.tsx
import { useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { MembersPanel } from '../../components/members'
import { Badge, Button, ConfirmDialog, EmptyState, Field, Input, Modal, Panel, Select } from '../../components/ui'
import { useAdmin } from '../../state/admin'
import * as admin from '../../api/admin'
import { addMember, removeMember, updateMember, type OrganizationMember } from '../../api/organization'
import { ORGANIZATION_STATUS_LABEL, ORGANIZATION_TYPE_LABEL } from '../../lib/adminFilters'
import { formatDate, labelFor, toDateTimeInput } from '../../lib/format'

const TONE = { PENDING: 'attention', VERIFIED: 'positif', REJECTED: 'negatif' } as const
type Identity = { legal_name: string; matricule_fiscal: string; governorate: string; city: string; address_line: string }

export default function AdminOrganisationDetail() {
  const { id = '' } = useParams()
  const { organizations, users, loading, reload } = useAdmin()
  const org = organizations.find((o) => o.id === id)
  const [editing, setEditing] = useState(false)
  const [form, setForm] = useState<Identity>({ legal_name: '', matricule_fiscal: '', governorate: '', city: '', address_line: '' })
  const [error, setError] = useState<string | null>(null)
  const [memberError, setMemberError] = useState<string | null>(null)
  const [refreshKey, setRefreshKey] = useState(0)
  const [adding, setAdding] = useState(false)
  const [editingMember, setEditingMember] = useState<OrganizationMember | null>(null)
  const [removing, setRemoving] = useState<OrganizationMember | null>(null)

  if (!org) {
    return (
      <>
        <PageHeader title="Organisation" />
        <PageBody>{loading ? <p className="text-slate">Chargement…</p> : <EmptyState title="Organisation introuvable" action={<Link to="/admin/organisations" className="text-[13px] font-medium text-teal hover:underline">Retour à la liste</Link>} />}</PageBody>
      </>
    )
  }

  const startEditing = () => {
    setForm({ legal_name: org.legal_name, matricule_fiscal: org.matricule_fiscal, governorate: org.governorate, city: org.city, address_line: org.address_line })
    setError(null); setEditing(true)
  }
  const save = async () => {
    setError(null)
    // N’envoie que les champs modifiés : un matricule déjà en base, invalide pour le validateur, ne bloque pas une autre correction.
    const changed = Object.fromEntries(Object.entries(form).filter(([k, v]) => v !== org[k as keyof Identity])) as Partial<Identity>
    try { await admin.updateOrganization(org.id, changed); await reload(); setEditing(false) }
    catch (e) { setError(e instanceof Error ? e.message : 'Enregistrement refusé.') }
  }
  const field = (k: keyof Identity) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  return (
    <>
      <PageHeader title={org.legal_name} description={<Link to="/admin/organisations" className="text-teal hover:underline">Toutes les organisations</Link>} />
      <PageBody className="space-y-6">
        <Panel
          title="Identité"
          action={editing ? null : <Button size="sm" variant="secondaire" onClick={startEditing}>Modifier</Button>}
        >
          {editing ? (
            <div className="space-y-4 p-5">
              {error && <p role="alert" className="text-[13px] text-coral">{error}</p>}
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label="Raison sociale" required><Input value={form.legal_name} onChange={field('legal_name')} /></Field>
                <Field label="Matricule fiscal" required><Input value={form.matricule_fiscal} onChange={field('matricule_fiscal')} /></Field>
                <Field label="Gouvernorat"><Input value={form.governorate} onChange={field('governorate')} /></Field>
                <Field label="Ville"><Input value={form.city} onChange={field('city')} /></Field>
                <div className="sm:col-span-2"><Field label="Adresse"><Input value={form.address_line} onChange={field('address_line')} /></Field></div>
              </div>
              <div className="flex gap-2">
                <Button onClick={() => void save()} disabled={!form.legal_name.trim() || !form.matricule_fiscal.trim()}>Enregistrer</Button>
                <Button variant="secondaire" onClick={() => setEditing(false)}>Annuler</Button>
              </div>
            </div>
          ) : (
            <dl className="grid gap-4 p-5 text-[13.5px] sm:grid-cols-2">
              <div><dt className="text-[12px] text-slate">Type</dt><dd className="text-navy">{labelFor(ORGANIZATION_TYPE_LABEL, org.type, 'Autre type')}</dd></div>
              <div><dt className="text-[12px] text-slate">Statut</dt><dd><Badge tone={TONE[org.verification_status]}>{ORGANIZATION_STATUS_LABEL[org.verification_status]}</Badge></dd></div>
              <div><dt className="text-[12px] text-slate">Matricule fiscal</dt><dd className="tnum text-navy">{org.matricule_fiscal}</dd></div>
              <div><dt className="text-[12px] text-slate">Lieu</dt><dd className="text-navy">{[org.address_line, org.city, org.governorate].filter(Boolean).join(', ') || '—'}</dd></div>
            </dl>
          )}
        </Panel>

        {memberError && <p role="alert" className="text-coral">{memberError}</p>}
        <MembersPanel
          organizationId={org.id}
          refreshKey={refreshKey}
          action={<Button size="sm" onClick={() => setAdding(true)}>Ajouter un membre</Button>}
          rowAction={(member) => (
            <>
              <Button size="sm" variant="discret" onClick={() => setEditingMember(member)}>Modifier</Button>{' '}
              <Button size="sm" variant="danger" onClick={() => setRemoving(member)}>Retirer</Button>
            </>
          )}
        />

        {adding && (
          <MemberDialog
            title="Ajouter un membre"
            organizationId={org.id}
            candidates={users}
            onClose={() => setAdding(false)}
            onSaved={() => { setAdding(false); setRefreshKey((k) => k + 1) }}
          />
        )}
        {editingMember && (
          <MemberDialog
            title={`Modifier ${editingMember.first_name} ${editingMember.last_name}`}
            organizationId={org.id}
            member={editingMember}
            onClose={() => setEditingMember(null)}
            onSaved={() => { setEditingMember(null); setRefreshKey((k) => k + 1) }}
          />
        )}
        {removing && (
          <ConfirmDialog
            title="Retirer ce membre ?"
            danger
            onCancel={() => setRemoving(null)}
            onConfirm={() => {
              const target = removing
              setRemoving(null); setMemberError(null)
              removeMember(org.id, target.user)
                .then(() => setRefreshKey((k) => k + 1))
                .catch((e) => setMemberError(e instanceof Error ? e.message : 'Retrait refusé.'))
            }}
          >
            {removing.first_name} {removing.last_name} n’appartiendra plus à {org.legal_name} et perdra l’accès à son espace.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}

/** Ajout (choix d’un utilisateur existant) ou modification d’un membre. */
function MemberDialog({
  title,
  organizationId,
  member,
  candidates = [],
  onClose,
  onSaved,
}: {
  title: string
  organizationId: string
  member?: OrganizationMember
  candidates?: admin.AdminUser[]
  onClose: () => void
  onSaved: () => void
}) {
  const [userId, setUserId] = useState('')
  const [jobTitle, setJobTitle] = useState(member?.job_title ?? '')
  const [joinedAt, setJoinedAt] = useState(member?.joined_at ? toDateTimeInput(member.joined_at) : '')
  const [error, setError] = useState<string | null>(null)
  const joined = joinedAt ? new Date(joinedAt).toISOString() : null

  async function save() {
    setError(null)
    try {
      if (member) await updateMember(organizationId, member.user, { job_title: jobTitle.trim(), joined_at: joined })
      else await addMember(organizationId, { user: userId, job_title: jobTitle.trim(), joined_at: joined })
      onSaved()
    } catch (e) { setError(e instanceof Error ? e.message : 'Enregistrement refusé.') }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={title}
      footer={
        <>
          <Button variant="secondaire" onClick={onClose}>Annuler</Button>
          <Button disabled={!member && !userId} onClick={() => void save()}>Enregistrer</Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <p role="alert" className="text-[13px] text-coral">{error}</p>}
        {!member && (
          <Field label="Utilisateur" required>
            <Select value={userId} onChange={(e) => setUserId(e.target.value)}>
              <option value="">Choisir…</option>
              {candidates.map((u) => <option key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.email})</option>)}
            </Select>
          </Field>
        )}
        <Field label="Fonction"><Input value={jobTitle} onChange={(e) => setJobTitle(e.target.value)} /></Field>
        <Field label="Membre depuis"><Input type="datetime-local" value={joinedAt} onChange={(e) => setJoinedAt(e.target.value)} /></Field>
        {member?.joined_at && <p className="text-[12px] text-slate">Dernière date : {formatDate(member.joined_at)}</p>}
      </div>
    </Modal>
  )
}
