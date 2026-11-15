// Placement: frontend/src/pages/candidat/AtsExport.tsx
import { useState } from 'react'
import { Button, ConfirmDialog, Field, Note, Select } from '../../components/ui'
import { downloadGeneratedCV, saveGeneratedCV, type AtsAnalysis, type CvFileFormat } from '../../api/candidate'

/** Download the CV draft as an ATS-friendly DOCX or PDF, or save it as a new CV version after confirmation. */
export default function AtsExport({ analysis, onSaved }: { analysis: AtsAnalysis; onSaved: () => Promise<void> }) {
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [saved, setSaved] = useState('')
  const [confirming, setConfirming] = useState(false)
  const [saveFormat, setSaveFormat] = useState<CvFileFormat>('pdf')
  const draft = analysis.cv_draft_json
  const texts = [...Object.values(draft.bullets ?? {}).filter((choice) => choice.decision === 'accept').map((choice) => choice.text), draft.summary ?? '']
  // Pre-download hint with the server's placeholder pattern (rewrite.py PLACEHOLDER); the file response also carries X-CV-Placeholders.
  const placeholders = texts.reduce((count, text) => count + (text.match(/\[X[^[\]\n\d]{0,18}\]/g)?.length ?? 0), 0)

  async function run(work: () => Promise<unknown>, failure: string) {
    setBusy(true); setError('')
    try { await work() } catch { setError(failure) } finally { setBusy(false) }
  }
  const download = (fileFormat: CvFileFormat) => run(() => downloadGeneratedCV(analysis.id, fileFormat, `cv-ats.${fileFormat}`), 'Le téléchargement a échoué. Réessayez plus tard.')
  const confirmSave = () => {
    setConfirming(false); setSaved('')
    void run(async () => { const cv = await saveGeneratedCV(analysis.id, saveFormat); await onSaved(); setSaved(`Nouvelle version v${cv.version_number} enregistrée dans vos CV.`) }, 'L’enregistrement a échoué. Réessayez plus tard.')
  }

  return <section aria-label="Générer le CV" className="space-y-3">
    <div>
      <h3 className="mb-1 text-sm font-semibold text-navy">CV optimisé pour les ATS</h3>
      <p className="text-[12px] text-slate">Une seule colonne, titres standard en anglais dans l’ordre recommandé pour le poste, sans tableau, icône ni image. Votre CV d’origine et votre profil ne sont pas modifiés.</p>
    </div>
    {placeholders > 0 && <Note tone="attention">{placeholders} espace(s) réservé(s) [X] restent à remplacer par vos vrais chiffres avant d’envoyer ce CV.</Note>}
    {error && <p role="alert" className="text-coral">{error}</p>}
    {saved && <p role="status" className="text-sm text-leaf">{saved}</p>}
    <div className="flex flex-wrap gap-2">
      <Button size="sm" variant="secondaire" disabled={busy} onClick={() => void download('docx')}>Télécharger en DOCX</Button>
      <Button size="sm" variant="secondaire" disabled={busy} onClick={() => void download('pdf')}>Télécharger en PDF</Button>
      <Button size="sm" disabled={busy} onClick={() => setConfirming(true)}>Enregistrer comme nouvelle version</Button>
    </div>
    {confirming && <ConfirmDialog title="Enregistrer comme nouvelle version de CV ?" onCancel={() => setConfirming(false)} onConfirm={confirmSave}>
      <p>Le CV généré sera ajouté à vos CV comme nouvelle version, sans devenir votre CV principal. Vous pourrez l’utiliser pour postuler.</p>
      {placeholders > 0 && <p>Attention : il contient encore {placeholders} espace(s) réservé(s) [X].</p>}
      <Field label="Format"><Select value={saveFormat} onChange={(event) => setSaveFormat(event.target.value as CvFileFormat)}><option value="pdf">PDF</option><option value="docx">DOCX</option></Select></Field>
    </ConfirmDialog>}
  </section>
}
