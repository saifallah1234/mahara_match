// Placement: frontend/src/pages/candidat/AtsPanel.tsx
import { useEffect, useState } from 'react'
import { Badge, Button, EmptyState, Field, Meter, Note, Panel, Select, StatTile } from '../../components/ui'
import { analyseCV, analyses, reviewRoles, type AtsAnalysis, type CV, type ReviewLevel, type ReviewRole } from '../../api/candidate'
import { ApiError } from '../../api/client'
import AtsDraft from './AtsDraft'
import AtsExport from './AtsExport'

const LEVELS: { id: ReviewLevel; label: string }[] = [
  { id: 'intern', label: 'Stagiaire' },
  { id: 'junior', label: 'Junior' },
  { id: 'mid', label: 'Confirmé' },
]
const COMPONENTS: Record<string, string> = {
  parseability: 'Lisibilité et format',
  sections: 'Sections et ordre',
  skill_coverage: 'Couverture des compétences du poste',
  evidence: 'Preuves dans les expériences et projets',
  content: 'Qualité des puces (verbes, chiffres)',
  length: 'Longueur',
}
const SEVERITY = { high: ['negatif', 'Important'], medium: ['attention', 'À revoir'], low: ['neutre', 'Conseil'] } as const

function errorMessage(failure: unknown) {
  const message = failure instanceof Error ? failure.message : ''
  if (message.includes('English')) return 'Seuls les CV rédigés en anglais peuvent être analysés pour le moment.'
  if (message.includes('PDF and DOCX')) return 'Seuls les fichiers PDF et DOCX peuvent être analysés.'
  if (failure instanceof ApiError && failure.status === 404) return 'Ce CV est introuvable ou a été supprimé.'
  return 'L’analyse a échoué. Réessayez plus tard.'
}

export default function AtsPanel({ cvs, onSaved }: { cvs: CV[]; onSaved: () => Promise<void> }) {
  const [roles, setRoles] = useState<ReviewRole[]>([])
  const [cvId, setCvId] = useState('')
  const [role, setRole] = useState('')
  const [level, setLevel] = useState<ReviewLevel>('junior')
  const [result, setResult] = useState<AtsAnalysis>()
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  useEffect(() => { reviewRoles().then((items) => { setRoles(items); setRole((current) => current || items[0]?.id || '') }).catch(() => setError('Les rôles ne sont pas disponibles.')) }, [])
  const selectedCv = cvId || cvs.find((cv) => cv.is_primary)?.id || cvs[0]?.id || ''
  // The latest analysis of the selected CV, so its draft survives leaving and returning.
  useEffect(() => {
    if (!selectedCv) return
    let current = true
    setResult(undefined)
    // A fresh run() result wins over this late load.
    analyses().then((items) => { if (current) setResult((shown) => shown ?? items.find((item) => item.cv === selectedCv)) }).catch(() => undefined)
    return () => { current = false }
  }, [selectedCv])

  async function run() {
    setBusy(true); setError('')
    try { setResult(await analyseCV(selectedCv, role, level)) }
    catch (failure) { setResult(undefined); setError(errorMessage(failure)) }
    finally { setBusy(false) }
  }

  if (!cvs.length) return <Panel title="Analyse ATS"><EmptyState title="Importez un CV pour l’analyser">Utilisez le formulaire « Importer un CV » de cette page.</EmptyState></Panel>
  const breakdown = result?.breakdown_json
  return <Panel title="Analyse ATS" description="Évalue la lisibilité de votre CV par un ATS (ATS readiness) et son adéquation au poste visé (role fit). Ce n’est pas un score ATS universel : chaque logiciel de recrutement lit les CV à sa manière.">
    <div className="space-y-5 p-5">
      <div className="grid gap-4 sm:grid-cols-3">
        <Field label="CV"><Select value={selectedCv} onChange={(event) => setCvId(event.target.value)}>{cvs.map((cv) => <option key={cv.id} value={cv.id}>v{cv.version_number} — {cv.title}</option>)}</Select></Field>
        <Field label="Poste visé"><Select value={role} onChange={(event) => setRole(event.target.value)}>{roles.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</Select></Field>
        <Field label="Niveau"><Select value={level} onChange={(event) => setLevel(event.target.value as ReviewLevel)}>{LEVELS.map((item) => <option key={item.id} value={item.id}>{item.label}</option>)}</Select></Field>
      </div>
      <p className="text-[12px] text-slate">CV en anglais uniquement, au format PDF ou DOCX. Votre profil n’est pas modifié par l’analyse.</p>
      <Button onClick={() => void run()} disabled={busy || !role || !selectedCv}>{busy ? 'Analyse en cours…' : 'Analyser'}</Button>
      {error && <p role="alert" className="text-coral">{error}</p>}
      {result && breakdown && <div className="space-y-5">
        <div className="grid gap-3 sm:grid-cols-2">
          <StatTile value={`${Math.round(breakdown.ats_readiness)} / 100`} label="Lisibilité ATS (ATS readiness)" note="Format, sections, rédaction et longueur" tone="teal" />
          <StatTile value={`${Math.round(breakdown.role_fit)} / 100`} label={`Adéquation au poste (role fit) — ${roles.find((item) => item.id === result.role_profile_id)?.label ?? result.role_profile_id}`} note="Compétences du poste et preuves dans vos expériences" tone="leaf" />
        </div>
        <div className="space-y-3">{Object.entries(COMPONENTS).map(([key, label]) => <Meter key={key} label={label} value={Math.round(breakdown.components[key] ?? 0)} />)}</div>
        {breakdown.parse_degraded && <Note tone="attention">La structure du CV a été lue de manière simplifiée.</Note>}
        <div>
          <h3 className="mb-2 text-sm font-semibold text-navy">Points à améliorer</h3>
          {!result.issues_json.length ? <p className="text-sm text-slate">Aucun problème détecté.</p> : <ul className="space-y-2">{result.issues_json.map((issue) => {
            const [tone, label] = SEVERITY[issue.severity]
            return <li key={issue.code} className="flex gap-2 text-sm text-navy"><Badge tone={tone}>{label}</Badge><span>{issue.message}</span></li>
          })}</ul>}
        </div>
        <AtsDraft key={result.id} analysis={result} onChange={setResult} />
        <AtsExport key={`export-${result.id}`} analysis={result} onSaved={onSaved} />
      </div>}
    </div>
  </Panel>
}
