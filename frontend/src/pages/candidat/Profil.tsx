import { useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, Field, Input, Panel, Select, Textarea } from '../../components/ui'
import { SkillChip } from '../../components/domain'
import { useCandidate } from '../../state/candidate'
import { useAuth } from '../../state/auth'
import { list, type OwnedRecord, type RecordKind } from '../../api/candidate'
import { GOUVERNORATS, skillLabel } from '../../lib/format'
import { PROFILE_SECTIONS, PROFILE_SECTION_LABEL as labels } from '../../lib/candidateProfile'

type FieldSpec = { name: string; label: string; type?: string; required?: boolean; options?: string[]; catalogue?: 'skills' | 'languages' | 'education' }
const levels = ['BEGINNER', 'INTERMEDIATE', 'ADVANCED', 'EXPERT']
const optionLabels: Record<string, string> = {
  BEGINNER: 'Débutant', INTERMEDIATE: 'Intermédiaire', ADVANCED: 'Avancé', EXPERT: 'Expert',
  ONSITE: 'Sur site', HYBRID: 'Hybride', REMOTE: 'À distance', OPEN: 'Mobile', CANNOT: 'Non mobile',
}
const fields: Record<RecordKind, FieldSpec[]> = {
  experiences: [{ name: 'job_title', label: 'Poste', required: true }, { name: 'organization_name', label: 'Organisation', required: true }, { name: 'start_date', label: 'Début', type: 'date', required: true }, { name: 'end_date', label: 'Fin', type: 'date' }, { name: 'description', label: 'Description' }],
  educations: [{ name: 'education_level', label: 'Niveau', catalogue: 'education', required: true }, { name: 'institution', label: 'Établissement', required: true }, { name: 'field_of_study', label: 'Domaine' }, { name: 'start_year', label: 'Début', type: 'number', required: true }, { name: 'end_year', label: 'Fin', type: 'number' }, { name: 'description', label: 'Description' }],
  skills: [{ name: 'skill', label: 'Compétence', catalogue: 'skills', required: true }, { name: 'level', label: 'Niveau', options: levels, required: true }, { name: 'years_experience', label: 'Années d’expérience', type: 'number' }],
  languages: [{ name: 'language', label: 'Langue', catalogue: 'languages', required: true }, { name: 'level', label: 'Niveau', options: ['A1', 'A2', 'B1', 'B2', 'C1', 'C2'], required: true }],
  certifications: [{ name: 'name', label: 'Certification', required: true }, { name: 'certification_organization', label: 'Organisme', required: true }, { name: 'description', label: 'Description' }, { name: 'issue_date', label: 'Date', type: 'date', required: true }, { name: 'expiration_date', label: 'Expiration', type: 'date' }, { name: 'credential_id', label: 'Identifiant' }, { name: 'credential_url', label: 'Lien', type: 'url' }],
  projects: [{ name: 'name', label: 'Projet', required: true }, { name: 'role', label: 'Rôle' }, { name: 'description', label: 'Description' }, { name: 'start_date', label: 'Début', type: 'date' }, { name: 'end_date', label: 'Fin', type: 'date' }, { name: 'project_url', label: 'Lien', type: 'url' }, { name: 'repository_url', label: 'Dépôt', type: 'url' }],
  preferences: [{ name: 'work_mode', label: 'Mode de travail', options: ['ONSITE', 'HYBRID', 'REMOTE'], required: true }, { name: 'relocation', label: 'Mobilité', options: ['OPEN', 'CANNOT'] }, { name: 'distance', label: 'Distance maximale (km)', type: 'number' }],
}
const hints: Record<RecordKind, string> = {
  experiences: 'Vos postes et stages précédents.', educations: 'Vos diplômes et formations académiques.',
  skills: 'Elles servent au calcul de votre compatibilité avec les offres.', certifications: 'Les certificats obtenus et leur organisme.',
  projects: 'Des réalisations qui montrent vos compétences.', languages: 'Les langues que vous parlez et votre niveau.',
  preferences: 'Mode de travail et mobilité souhaités.',
}
const sectionId = (kind: RecordKind | 'identity') => `profil-${kind}`
const jumpTo = (kind: RecordKind | 'identity') => document.getElementById(sectionId(kind))?.scrollIntoView({ behavior: 'smooth', block: 'start' })
type Reference = { id: string; canonical_name?: string; name?: string; code?: string }

export default function CandidatProfil() {
  const { user } = useAuth()
  const { profile, records, saveIdentity, saveRecord, deleteRecord } = useCandidate()
  const [identity, setIdentity] = useState({ first_name: '', last_name: '', phone: '', birth_date: '', country_code: '', governorate: '', city: '', headline: '', summary: '', employment_status: '', desired_job_title: '', availability_date: '', profile_visibility: 'PRIVATE' })
  const [editing, setEditing] = useState<{ kind: RecordKind; id?: string } | null>(null)
  const [deleting, setDeleting] = useState<{ kind: RecordKind; record: OwnedRecord } | null>(null)
  const [draft, setDraft] = useState<Record<string, string>>({})
  const [projectTechnologies, setProjectTechnologies] = useState<string[]>([])
  const [references, setReferences] = useState<Record<string, Reference[]>>({ skills: [], languages: [], education: [] })
  const [referenceError, setReferenceError] = useState('')
  const [busy, setBusy] = useState(false)
  const [params] = useSearchParams()
  const section = params.get('section') as RecordKind | null
  useEffect(() => { if (user && profile) setIdentity({ first_name: user.first_name, last_name: user.last_name, phone: user.phone ?? '', birth_date: profile.birth_date ?? '', country_code: profile.country_code, governorate: profile.governorate, city: profile.city, headline: profile.headline, summary: profile.summary, employment_status: profile.employment_status, desired_job_title: profile.desired_job_title, availability_date: profile.availability_date ?? '', profile_visibility: profile.profile_visibility }) }, [user?.id, profile?.id])
  useEffect(() => { let live = true; void Promise.all([list<Reference>('/skills/'), list<Reference>('/languages/'), list<Reference>('/education-levels/')]).then(([skills, languages, education]) => { if (live) setReferences({ skills, languages, education }) }).catch(() => { if (live) setReferenceError('Référentiels indisponibles.') }); return () => { live = false } }, [])
  // The dashboard links here with ?section=… to point at the next section to fill.
  useEffect(() => { if (profile && section) jumpTo(section) }, [profile?.id, section])
  if (!profile) return <PageBody><Panel className="p-5">Profil indisponible.</Panel></PageBody>
  async function identitySubmit(event: FormEvent) {
    event.preventDefault(); setBusy(true)
    try { await saveIdentity({ first_name: identity.first_name, last_name: identity.last_name, phone: identity.phone }, { birth_date: identity.birth_date || null, country_code: identity.country_code, governorate: identity.governorate, city: identity.city, headline: identity.headline, summary: identity.summary, employment_status: identity.employment_status, desired_job_title: identity.desired_job_title, availability_date: identity.availability_date || null, profile_visibility: identity.profile_visibility as 'PRIVATE' | 'RECRUITERS' | 'PUBLIC' }) }
    catch { /* The workspace shows the API error. */ } finally { setBusy(false) }
  }
  function begin(kind: RecordKind, record?: OwnedRecord) {
    setEditing({ kind, id: record?.id })
    setDraft(Object.fromEntries(fields[kind].map((field) => [field.name, record?.[field.name] == null ? '' : String(record[field.name]) ])))
    setProjectTechnologies(Array.isArray(record?.technologies) ? record.technologies.map(String) : [])
  }
  async function recordSubmit(event: FormEvent) {
    event.preventDefault(); if (!editing) return
    const values: Record<string, string | number | null | string[]> = {}
    for (const field of fields[editing.kind]) {
      const value = draft[field.name] ?? ''
      values[field.name] = field.type === 'number' ? (value ? Number(value) : null) : (field.type === 'date' ? value || null : value)
    }
    if (editing.kind === 'projects') values.technologies = projectTechnologies
    setBusy(true)
    try { await saveRecord(editing.kind, values, editing.id); setEditing(null) }
    catch { /* The workspace shows the API error. */ } finally { setBusy(false) }
  }
  return <>
    <PageHeader title="Mon profil" />
    <PageBody className="space-y-5">
      {referenceError && <p role="alert" className="text-coral">{referenceError}</p>}
      <nav aria-label="Sections du profil" className="flex flex-wrap gap-2">
        {(['identity', ...PROFILE_SECTIONS] as const).map((kind) => <Button key={kind} size="sm" variant="secondaire" onClick={() => jumpTo(kind)}>{kind === 'identity' ? 'Identité' : labels[kind]}</Button>)}
      </nav>
      <div id={sectionId('identity')} className="scroll-mt-28"><Panel title="Identité et présentation"><form onSubmit={(event) => void identitySubmit(event)} className="grid gap-4 p-5 sm:grid-cols-2">
        <Field label="Prénom" required><Input required value={identity.first_name} onChange={(event) => setIdentity({ ...identity, first_name: event.target.value })} /></Field>
        <Field label="Nom" required><Input required value={identity.last_name} onChange={(event) => setIdentity({ ...identity, last_name: event.target.value })} /></Field>
        <Field label="Adresse e-mail"><Input value={user?.email ?? ''} readOnly /></Field>
        <Field label="Téléphone"><Input value={identity.phone} onChange={(event) => setIdentity({ ...identity, phone: event.target.value })} /></Field>
        <Field label="Date de naissance"><Input type="date" value={identity.birth_date} onChange={(event) => setIdentity({ ...identity, birth_date: event.target.value })} /></Field>
        <Field label="Code pays"><Input maxLength={2} value={identity.country_code} onChange={(event) => setIdentity({ ...identity, country_code: event.target.value.toUpperCase() })} /></Field>
        <Field label="Gouvernorat"><Select value={identity.governorate} onChange={(event) => setIdentity({ ...identity, governorate: event.target.value })}><option value="">Non renseigné</option>{GOUVERNORATS.map((name) => <option key={name}>{name}</option>)}</Select></Field>
        <Field label="Ville"><Input value={identity.city} onChange={(event) => setIdentity({ ...identity, city: event.target.value })} /></Field>
        <Field label="Titre d’accroche"><Input value={identity.headline} onChange={(event) => setIdentity({ ...identity, headline: event.target.value })} /></Field>
        <Field label="Poste recherché"><Input value={identity.desired_job_title} onChange={(event) => setIdentity({ ...identity, desired_job_title: event.target.value })} /></Field>
        <Field label="Situation professionnelle"><Input value={identity.employment_status} onChange={(event) => setIdentity({ ...identity, employment_status: event.target.value })} /></Field>
        <Field label="Disponibilité"><Input type="date" value={identity.availability_date} onChange={(event) => setIdentity({ ...identity, availability_date: event.target.value })} /></Field>
        <div className="sm:col-span-2"><Field label="Présentation"><Textarea value={identity.summary} onChange={(event) => setIdentity({ ...identity, summary: event.target.value })} /></Field></div>
        <Field label="Visibilité"><Select value={identity.profile_visibility} onChange={(event) => setIdentity({ ...identity, profile_visibility: event.target.value })}><option value="PRIVATE">Privée</option><option value="RECRUITERS">Recruteurs</option><option value="PUBLIC">Publique</option></Select></Field>
        <div className="sm:col-span-2"><Button type="submit" disabled={busy}>Enregistrer le profil</Button></div>
      </form></Panel></div>
      {PROFILE_SECTIONS.map((kind) => <div key={kind} id={sectionId(kind)} className="scroll-mt-28">{!records[kind].length && editing?.kind !== kind
        ? <section className="flex flex-wrap items-center justify-between gap-3 rounded-[10px] border border-line bg-white px-5 py-3 shadow-panel">
          <p className="text-sm"><span className="font-semibold text-navy">{labels[kind]}</span> <span className="text-slate">· {hints[kind]}</span></p>
          <Button size="sm" variant="secondaire" onClick={() => begin(kind)}>Ajouter</Button>
        </section>
        : <Panel title={labels[kind]} action={kind !== 'preferences' || !records.preferences.length ? <Button size="sm" variant="secondaire" onClick={() => begin(kind)}>Ajouter</Button> : undefined}>
        <ul className="divide-y divide-line">{records[kind].map((record) => <li key={record.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3"><div className="min-w-0 break-words text-sm text-navy">{fields[kind].map((field) => {
          const value = record[field.name]
          if (value == null || value === '') return null
          const reference = field.catalogue ? references[field.catalogue].find((entry) => entry.id === value) : null
          if (kind === 'skills' && field.name === 'skill' && reference?.canonical_name) return <span key={field.name} className="mr-2"><SkillChip name={reference.canonical_name} /></span>
          return <span key={field.name} className="mr-2">{(reference?.canonical_name && skillLabel(reference.canonical_name)) || reference?.name || reference?.code || optionLabels[String(value)] || String(value)}</span>
        })}{kind === 'skills' && record.validated === false && <Badge tone="neutre">Déclarée</Badge>}</div><div className="flex shrink-0 gap-2"><Button size="sm" variant="discret" onClick={() => begin(kind, record)}>Modifier</Button><Button size="sm" variant="danger" onClick={() => setDeleting({ kind, record })}>Supprimer</Button></div></li>)}</ul>
        {editing?.kind === kind && <form onSubmit={(event) => void recordSubmit(event)} className="grid gap-3 border-t border-line p-5 sm:grid-cols-2">{fields[kind].map((field) => <Field key={field.name} label={field.label} required={field.required}>
          {field.options || field.catalogue ? <Select required={field.required} value={draft[field.name] ?? ''} onChange={(event) => setDraft({ ...draft, [field.name]: event.target.value })}><option value="">Choisir</option>{field.options?.map((value) => <option key={value} value={value}>{optionLabels[value] ?? value}</option>)}{field.catalogue && references[field.catalogue].map((entry) => <option key={entry.id} value={entry.id}>{(entry.canonical_name && skillLabel(entry.canonical_name)) || entry.name || entry.code}</option>)}</Select>
            : field.name === 'description' ? <Textarea value={draft[field.name] ?? ''} onChange={(event) => setDraft({ ...draft, [field.name]: event.target.value })} />
              : <Input type={field.type ?? 'text'} required={field.required} min={field.type === 'number' ? 0 : undefined} value={draft[field.name] ?? ''} onChange={(event) => setDraft({ ...draft, [field.name]: event.target.value })} />}
        </Field>)}{kind === 'projects' && <fieldset className="sm:col-span-2"><legend className="text-sm font-medium text-navy">Technologies</legend><div className="mt-2 max-h-40 overflow-y-auto rounded border border-line p-2">{references.skills.map((skill) => <label key={skill.id} className="mr-4 inline-flex items-center gap-1 text-sm"><input type="checkbox" checked={projectTechnologies.includes(skill.id)} onChange={(event) => setProjectTechnologies(event.target.checked ? [...projectTechnologies, skill.id] : projectTechnologies.filter((id) => id !== skill.id))} />{skillLabel(skill.canonical_name ?? '')}</label>)}</div></fieldset>}<div className="flex gap-2 sm:col-span-2"><Button type="submit" disabled={busy}>Enregistrer</Button><Button type="button" variant="secondaire" onClick={() => setEditing(null)}>Annuler</Button></div></form>}
      </Panel>}</div>)}
      {deleting && (
        <ConfirmDialog
          title="Supprimer cet élément ?"
          danger
          onCancel={() => setDeleting(null)}
          onConfirm={() => {
            void deleteRecord(deleting.kind, deleting.record.id).catch(() => {})
            if (editing?.id === deleting.record.id) setEditing(null)
            setDeleting(null)
          }}
        >
          Il sera retiré de votre profil.
        </ConfirmDialog>
      )}
    </PageBody>
  </>
}
