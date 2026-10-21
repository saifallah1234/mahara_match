import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, Field, Input, Panel, Select, Textarea } from '../../components/ui'
import { useAuth } from '../../state/auth'
import { useRecruiter } from '../../state/recruiter'
import { CONTRACT_OPTIONS, EXPERIENCE_OPTIONS, GOUVERNORATS, contractLabel } from '../../lib/format'

const MODES = [['ONSITE', 'Sur site'], ['HYBRID', 'Hybride'], ['REMOTE', 'À distance']]

export default function RecruteurNouvelleOffre() {
  const { workspace } = useAuth()
  const { skills, createOffer } = useRecruiter()
  const navigate = useNavigate()

  const [f, setF] = useState({
    title: '', description: '', contract_type: 'CDI', work_mode: 'ONSITE', experience_level: 'Débutant',
    governorate: 'Ariana', city: '', min: '', max: '', deadline: '',
  })
  const [easy, setEasy] = useState(true)
  const [chosen, setChosen] = useState<{ id: string; mandatory: boolean }[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (k: keyof typeof f) => (e: { target: { value: string } }) => setF({ ...f, [k]: e.target.value })
  const orgId = workspace?.organization?.id
  const skillName = (id: string) => skills.find((s) => s.id === id)?.canonical_name ?? id

  const problems: string[] = []
  if (!f.title.trim()) problems.push('Le titre est obligatoire.')
  if (!f.description.trim()) problems.push('La description est obligatoire.')
  if (chosen.length === 0) problems.push('Au moins une compétence est requise pour publier.')
  if (f.min && f.max && Number(f.max) < Number(f.min)) problems.push('Le salaire maximum doit être supérieur ou égal au minimum.')

  async function submit(publish: boolean) {
    if (!orgId) return
    setBusy(true); setError(null)
    try {
      await createOffer({
        organization_id: orgId, title: f.title.trim(), description: f.description.trim(),
        contract_type: f.contract_type, work_mode: f.work_mode, experience_level: f.experience_level,
        governorate: f.governorate, city: f.city.trim(),
        min_salary: f.min ? Number(f.min) : null, max_salary: f.max ? Number(f.max) : null,
        application_deadline: f.deadline || null, easy_apply: easy,
      }, chosen, publish)
      navigate('/recruteur/offres')
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Échec de la création.')
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <PageHeader back={{ to: '/recruteur/offres', label: 'Mes offres' }} title="Publier une offre" />
      <PageBody className="space-y-6">
        <Panel title="Le poste">
          <div className="grid gap-4 p-5 sm:grid-cols-2">
            <div className="sm:col-span-2">
              <Field label="Intitulé" required><Input value={f.title} onChange={set('title')} /></Field>
            </div>
            <div className="sm:col-span-2">
              <Field label="Description" required><Textarea rows={6} value={f.description} onChange={set('description')} /></Field>
            </div>
            <Field label="Contrat">
              <Select value={f.contract_type} onChange={set('contract_type')}>
                {CONTRACT_OPTIONS.map((c) => <option key={c} value={c}>{contractLabel(c)}</option>)}
              </Select>
            </Field>
            <Field label="Mode de travail">
              <Select value={f.work_mode} onChange={set('work_mode')}>
                {MODES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </Select>
            </Field>
            <Field label="Expérience">
              <Select value={f.experience_level} onChange={set('experience_level')}>
                {EXPERIENCE_OPTIONS.map((c) => <option key={c}>{c}</option>)}
              </Select>
            </Field>
            <Field label="Gouvernorat">
              <Select value={f.governorate} onChange={set('governorate')}>
                {GOUVERNORATS.map((g) => <option key={g}>{g}</option>)}
              </Select>
            </Field>
            <Field label="Ville"><Input value={f.city} onChange={set('city')} /></Field>
            <Field label="Date limite"><Input type="date" value={f.deadline} onChange={set('deadline')} /></Field>
            <Field label="Salaire min (TND)"><Input type="number" value={f.min} onChange={set('min')} /></Field>
            <Field label="Salaire max (TND)"><Input type="number" value={f.max} onChange={set('max')} /></Field>
            <label className="flex items-center gap-2 text-[13.5px] sm:col-span-2">
              <input type="checkbox" checked={easy} onChange={(e) => setEasy(e.target.checked)} />
              Candidature simple sur la plateforme (Easy Apply)
            </label>
          </div>
        </Panel>

        <Panel title="Compétences">
          <div className="space-y-3 p-5">
            <Select
              value=""
              onChange={(e) => {
                const id = e.target.value
                if (id && !chosen.some((c) => c.id === id)) setChosen([...chosen, { id, mandatory: true }])
              }}
            >
              <option value="">Ajouter une compétence…</option>
              {skills.map((s) => <option key={s.id} value={s.id}>{s.canonical_name}</option>)}
            </Select>
            {chosen.map((c) => (
              <div key={c.id} className="flex items-center justify-between gap-3 text-[13.5px]">
                <span>{skillName(c.id)}</span>
                <span className="flex items-center gap-3">
                  <label>
                    <input
                      type="checkbox"
                      checked={c.mandatory}
                      onChange={() => setChosen(chosen.map((x) => (x.id === c.id ? { ...x, mandatory: !x.mandatory } : x)))}
                    /> obligatoire
                  </label>
                  <Button size="sm" variant="discret" onClick={() => setChosen(chosen.filter((x) => x.id !== c.id))}>Retirer</Button>
                </span>
              </div>
            ))}
          </div>
        </Panel>

        {(error || problems.length > 0) && (
          <ul role="alert" className="text-[13px] text-coral">
            {error && <li>{error}</li>}
            {problems.map((p) => <li key={p}>{p}</li>)}
          </ul>
        )}

        <div className="flex gap-2">
          <Button
            variant="discret"
            disabled={busy || !f.title.trim() || !f.description.trim() || !orgId}
            onClick={() => void submit(false)}
          >
            Enregistrer en brouillon
          </Button>
          <Button disabled={busy || problems.length > 0 || !orgId} onClick={() => void submit(true)}>
            Publier
          </Button>
        </div>
      </PageBody>
    </>
  )
}