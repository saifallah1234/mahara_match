// Placement: frontend/src/pages/candidat/CvImport.tsx
// « Remplir mon profil depuis un CV » : lecture du CV en arrière-plan, puis vérification ligne par ligne.
// Le CV n’est ni modifié ni évalué : seules les informations qu’il contient pré-remplissent le profil.
// Rien n’est ajouté au profil sans la confirmation du candidat (bouton « Ajouter »).

import { Fragment, useEffect, useState, type ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Badge, Button, Field, Input, Note, Panel, Select, Textarea } from '../../components/ui'
import * as api from '../../api/candidate'
import { applyPayload, draftFromProposal, incompleteCount, missingFields, selectedCount, type Draft, type Section } from '../../lib/cvProposal'

type Reference = { id: string; canonical_name?: string; name?: string; code?: string }
const POLL_MS = 5000
const SKILL_LEVELS = [['BEGINNER', 'Débutant'], ['INTERMEDIATE', 'Intermédiaire'], ['ADVANCED', 'Avancé'], ['EXPERT', 'Expert']]
const LANGUAGE_LEVELS = ['A1', 'A2', 'B1', 'B2', 'C1', 'C2']
const FIELD_LABEL: Record<string, string> = { job_title: 'poste', organization_name: 'organisation', start_date: 'date de début', education_level: 'niveau', institution: 'établissement', start_year: 'année de début', name: 'nom', level: 'niveau', language_id: 'langue', certification_organization: 'organisme', issue_date: 'date' }
const SECTION_LABEL: Record<Section, string> = { experiences: 'Expériences', educations: 'Diplômes', skills: 'Compétences', languages: 'Langues', certifications: 'Certifications', projects: 'Projets' }

export default function CvImport({ cvs, educationLevels, onUseIdentity, onApplied }: {
  cvs: api.CV[]
  educationLevels: Reference[]
  onUseIdentity: (identity: api.ProposedIdentity) => void
  onApplied: () => Promise<void>
}) {
  const [cvId, setCvId] = useState('')
  const [cv, setCv] = useState<api.CV | null>(null)
  const [proposal, setProposal] = useState<api.CVProposal | null>(null)
  const [draft, setDraft] = useState<Draft | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  // Le CV principal (sinon le plus récent) est proposé par défaut.
  useEffect(() => {
    if (cvId || !cvs.length) return
    setCvId((cvs.find((c) => c.is_primary) ?? [...cvs].sort((a, b) => b.version_number - a.version_number)[0]).id)
  }, [cvs, cvId])

  // Choosing another CV starts over; a reload of the list (after « Ajouter ») only refreshes its state.
  useEffect(() => { setProposal(null); setDraft(null); setNotice(null); setError(null) }, [cvId])
  useEffect(() => { setCv(cvs.find((c) => c.id === cvId) ?? null) }, [cvId, cvs])

  // Pendant la lecture, l’état du CV est relu toutes les 5 s ; à la fin, la proposition est chargée.
  useEffect(() => {
    if (!cv) return
    if (cv.parse_status === 'PARSED' && !proposal) { void loadProposal(cv.id); return }
    if (cv.parse_status !== 'PROCESSING') return
    const timer = window.setInterval(() => { void api.getCV(cv.id).then(setCv).catch(() => {}) }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [cv?.id, cv?.parse_status]) // eslint-disable-line react-hooks/exhaustive-deps

  async function loadProposal(id: string) {
    try { const result = await api.cvProposal(id); setProposal(result); setDraft(draftFromProposal(result)) }
    catch (e) { setError(e instanceof Error ? e.message : 'Proposition indisponible.') }
  }

  async function readCV() {
    if (!cv) return
    setError(null); setNotice(null); setProposal(null); setDraft(null); setBusy(true)
    try { setCv(await api.parseCV(cv.id)) }
    catch (e) { setError(e instanceof Error ? e.message : 'Lecture impossible.') }
    finally { setBusy(false) }
  }

  async function apply() {
    if (!cv || !draft) return
    setError(null); setBusy(true)
    try {
      const counts = await api.applyCVProposal(cv.id, applyPayload(draft))
      const added = Object.entries(counts).filter(([, n]) => n > 0).map(([section, n]) => `${n} ${SECTION_LABEL[section as Section].toLowerCase()}`)
      setNotice(added.length ? `Ajouté à votre profil : ${added.join(', ')}.` : 'Rien de nouveau à ajouter.')
      setDraft(null); setProposal(null)
      await onApplied()
    } catch (e) { setError(e instanceof Error ? e.message : 'Ajout refusé.') }
    finally { setBusy(false) }
  }

  function update<K extends Section>(section: K, index: number, values: Partial<Draft[K][number]>) {
    setDraft((current) => current && { ...current, [section]: current[section].map((row, i) => (i === index ? { ...row, ...values } : row)) })
  }

  if (!cvs.length) {
    return <Panel title="Remplir mon profil depuis un CV"><p className="p-5 text-sm text-slate">Importez d’abord un CV dans <Link className="text-teal underline" to="/candidat/cv">Mes CV</Link>, puis revenez ici.</p></Panel>
  }

  const status = cv?.parse_status ?? ''
  return (
    <Panel title="Remplir mon profil depuis un CV">
      <div className="space-y-4 p-5">
        <p className="text-sm text-slate">Gagnez du temps : nous lisons votre CV pour pré-remplir votre profil. Votre CV n’est pas modifié. Vous vérifiez chaque entrée et choisissez ce qui est ajouté : rien n’est enregistré sans votre accord.</p>
        <div className="flex flex-wrap items-end gap-3">
          <div className="min-w-[16rem] flex-1"><Field label="CV à lire"><Select value={cvId} onChange={(e) => setCvId(e.target.value)}>{cvs.map((c) => <option key={c.id} value={c.id}>v{c.version_number} — {c.title}</option>)}</Select></Field></div>
          <Button disabled={busy || status === 'PROCESSING'} onClick={() => void readCV()}>{status === 'PROCESSING' ? 'Lecture en cours…' : status === 'PARSED' ? 'Relire ce CV' : 'Lire mon CV'}</Button>
        </div>
        {status === 'PROCESSING' && <Note>Lecture du CV en cours. Selon le service disponible, cela prend de quelques secondes à une dizaine de minutes ; vous pouvez rester sur cette page, elle se met à jour toute seule.</Note>}
        {status === 'FAILED' && <Note tone="danger">La lecture du CV a échoué : {cv?.parsed_data_json?.error ?? 'raison inconnue'}. Vous pouvez réessayer.</Note>}
        {error && <p role="alert" className="text-sm text-coral">{error}</p>}
        {notice && <p role="status" className="text-sm text-teal-deep">{notice}</p>}
      </div>

      {proposal && draft && <>
        <Identity identity={proposal.identity} onUse={onUseIdentity} />
        <Rows title="Expériences" section="experiences" draft={draft} update={update} render={(row, i) => <>
          <Field label="Poste" required><Input value={row.job_title} onChange={(e) => update('experiences', i, { job_title: e.target.value })} /></Field>
          <Field label="Organisation" required><Input value={row.organization_name} onChange={(e) => update('experiences', i, { organization_name: e.target.value })} /></Field>
          <Field label="Début" required><Input type="date" value={row.start_date} onChange={(e) => update('experiences', i, { start_date: e.target.value })} /></Field>
          <Field label="Fin" hint="Vide si en cours."><Input type="date" value={row.end_date} onChange={(e) => update('experiences', i, { end_date: e.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Description"><Textarea rows={3} value={row.description} onChange={(e) => update('experiences', i, { description: e.target.value })} /></Field></div>
        </>} />
        <Rows title="Diplômes" section="educations" draft={draft} update={update} render={(row, i) => <>
          <div className="sm:col-span-2 text-[13px] text-slate">{row.degree}</div>
          <Field label="Niveau" required><Select value={row.education_level} onChange={(e) => update('educations', i, { education_level: e.target.value })}><option value="">Choisir</option>{educationLevels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}</Select></Field>
          <Field label="Établissement" required><Input value={row.institution} onChange={(e) => update('educations', i, { institution: e.target.value })} /></Field>
          <Field label="Domaine"><Input value={row.field_of_study} onChange={(e) => update('educations', i, { field_of_study: e.target.value })} /></Field>
          <div className="grid grid-cols-2 gap-3"><Field label="Début" required><Input type="number" value={row.start_year} onChange={(e) => update('educations', i, { start_year: e.target.value })} /></Field><Field label="Fin"><Input type="number" value={row.end_year} onChange={(e) => update('educations', i, { end_year: e.target.value })} /></Field></div>
        </>} />
        <Rows title="Compétences" section="skills" draft={draft} update={update} compact render={(row, i) => <>
          <div className="flex items-center gap-2"><Input value={row.name} onChange={(e) => update('skills', i, { name: e.target.value })} />{row.already ? <Badge>Déjà dans le profil</Badge> : row.isNew && <Badge tone="teal">Nouvelle</Badge>}</div>
          <Select aria-label="Niveau" value={row.level} onChange={(e) => update('skills', i, { level: e.target.value })}>{SKILL_LEVELS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</Select>
        </>} />
        <Rows title="Langues" section="languages" draft={draft} update={update} compact render={(row, i) => <>
          <div className="text-sm text-navy">{row.name} {row.proficiency && <span className="text-slate">({row.proficiency})</span>} {row.already ? <Badge>Déjà dans le profil</Badge> : !row.language_id && <Badge tone="attention">Langue non disponible</Badge>}</div>
          <Select aria-label="Niveau" disabled={!row.language_id} value={row.level} onChange={(e) => update('languages', i, { level: e.target.value })}><option value="">Niveau</option>{LANGUAGE_LEVELS.map((l) => <option key={l}>{l}</option>)}</Select>
        </>} />
        <Rows title="Certifications" section="certifications" draft={draft} update={update} render={(row, i) => <>
          <Field label="Certification" required><Input value={row.name} onChange={(e) => update('certifications', i, { name: e.target.value })} /></Field>
          <Field label="Organisme" required><Input value={row.certification_organization} onChange={(e) => update('certifications', i, { certification_organization: e.target.value })} /></Field>
          <Field label="Date" required><Input type="date" value={row.issue_date} onChange={(e) => update('certifications', i, { issue_date: e.target.value })} /></Field>
        </>} />
        <Rows title="Projets" section="projects" draft={draft} update={update} render={(row, i) => <>
          <Field label="Projet" required><Input value={row.name} onChange={(e) => update('projects', i, { name: e.target.value })} /></Field>
          <Field label="Dépôt"><Input value={row.repository_url} onChange={(e) => update('projects', i, { repository_url: e.target.value })} /></Field>
          <div className="sm:col-span-2"><Field label="Technologies" hint="Séparées par des virgules."><Input value={row.technologies} onChange={(e) => update('projects', i, { technologies: e.target.value })} /></Field></div>
          <div className="sm:col-span-2"><Field label="Description"><Textarea rows={3} value={row.description} onChange={(e) => update('projects', i, { description: e.target.value })} /></Field></div>
        </>} />
        <div className="flex flex-wrap items-center gap-3 border-t border-line p-5">
          <Button disabled={busy || selectedCount(draft) === 0 || incompleteCount(draft) > 0} onClick={() => void apply()}>Ajouter la sélection à mon profil ({selectedCount(draft)})</Button>
          {incompleteCount(draft) > 0 && <span className="text-sm text-coral">{incompleteCount(draft)} ligne(s) cochée(s) à compléter (champs obligatoires en rouge) ou à décocher.</span>}
          {proposal.provider && <span className="text-[12px] text-slate">Lu avec : {proposal.provider}</span>}
        </div>
      </>}
    </Panel>
  )
}

function Identity({ identity, onUse }: { identity: api.ProposedIdentity; onUse: (identity: api.ProposedIdentity) => void }) {
  const shown = [['Nom', `${identity.first_name} ${identity.last_name}`.trim()], ['Téléphone', identity.phone], ['Gouvernorat', identity.governorate], ['Ville', identity.city], ['Accroche', identity.headline], ['Présentation', identity.summary]].filter(([, v]) => v)
  if (!shown.length) return null
  return (
    <div className="border-t border-line p-5">
      <h3 className="mb-2 font-semibold text-navy">Identité et présentation</h3>
      <dl className="grid gap-1 text-sm sm:grid-cols-[10rem_1fr]">{shown.map(([k, v]) => <Fragment key={k}><dt className="text-slate">{k}</dt><dd className="text-navy">{v}</dd></Fragment>)}</dl>
      <Button className="mt-3" size="sm" variant="secondaire" onClick={() => onUse(identity)}>Reprendre dans le formulaire</Button>
      <p className="mt-1 text-[12px] text-slate">Les champs vides de votre formulaire sont remplis ; vérifiez-les puis cliquez sur « Enregistrer le profil ».</p>
    </div>
  )
}

function Rows<K extends Section>({ title, section, draft, update, render, compact }: {
  title: string; section: K; draft: Draft; compact?: boolean
  update: (section: K, index: number, values: Partial<Draft[K][number]>) => void
  render: (row: Draft[K][number], index: number) => ReactNode
}) {
  const rows = draft[section] as Draft[K][number][]
  if (!rows.length) return null
  return (
    <div className="border-t border-line p-5">
      <h3 className="mb-3 font-semibold text-navy">{title} <span className="text-sm font-normal text-slate">({rows.filter((r) => r.include).length}/{rows.length} sélectionnées)</span></h3>
      <ul className={compact ? 'space-y-2' : 'space-y-4'}>{rows.map((row, i) => {
        const missing = missingFields(section, row)
        return (
          <li key={i} className={`rounded border p-3 ${missing.length ? 'border-coral' : 'border-line'} ${row.include ? '' : 'opacity-60'}`}>
            <label className="mb-2 inline-flex items-center gap-2 text-sm font-medium text-navy"><input type="checkbox" checked={row.include} onChange={(e) => update(section, i, { include: e.target.checked } as Partial<Draft[K][number]>)} />Ajouter{row.already && section !== 'skills' && section !== 'languages' && <Badge>Déjà dans le profil</Badge>}</label>
            <div className={compact ? 'grid gap-2 sm:grid-cols-[1fr_12rem]' : 'grid gap-3 sm:grid-cols-2'}>{render(row, i)}</div>
            {missing.length > 0 && <p className="mt-1 text-[12px] text-coral">À compléter : {missing.map((f) => FIELD_LABEL[f] ?? f).join(', ')}</p>}
          </li>
        )
      })}</ul>
    </div>
  )
}
