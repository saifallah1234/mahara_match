import { useState, type FormEvent } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Field, Input, Panel } from '../../components/ui'
import { download } from '../../api/candidate'
import { useCandidate } from '../../state/candidate'
import { formatDate } from '../../lib/format'
import AtsPanel from './AtsPanel'

export default function CandidatCV() {
  const { cvs, documents, uploadCV, setPrimary, deleteCV, reload } = useCandidate()
  const [file, setFile] = useState<File | null>(null)
  const [title, setTitle] = useState('')
  const [retryDocumentId, setRetryDocumentId] = useState<string>()
  const [busy, setBusy] = useState(false)
  const [downloadError, setDownloadError] = useState('')
  const [deleting, setDeleting] = useState<(typeof cvs)[number] | null>(null)
  async function submit(event: FormEvent) {
    event.preventDefault()
    if (!file) return
    setBusy(true)
    try { await uploadCV(file, title || file.name, retryDocumentId); setFile(null); setTitle(''); setRetryDocumentId(undefined) }
    catch (failure) { setRetryDocumentId((failure as { documentId?: string }).documentId) }
    finally { setBusy(false) }
  }
  async function action(work: () => Promise<unknown>) {
    setBusy(true)
    try { setDownloadError(''); await work() } catch (failure) { setDownloadError(failure instanceof Error ? failure.message : 'Téléchargement impossible.') }
    finally { setBusy(false) }
  }
  return <>
    <PageHeader title="Mes CV" />
    <PageBody className="space-y-5">
      {downloadError && <p role="alert" className="text-coral">{downloadError}</p>}
      <Panel title="Importer un CV"><form onSubmit={(event) => void submit(event)} className="space-y-4 p-5">
        <Field label="Fichier PDF, DOCX, JPEG ou PNG" required><Input type="file" accept=".pdf,.docx,.jpg,.jpeg,.png,application/pdf,application/vnd.openxmlformats-officedocument.wordprocessingml.document,image/jpeg,image/png" required onChange={(event) => { setFile(event.target.files?.[0] ?? null); setRetryDocumentId(undefined) }} /></Field>
        <Field label="Titre du CV"><Input value={title} onChange={(event) => setTitle(event.target.value)} placeholder="Mon CV" /></Field>
        <Button type="submit" disabled={!file || busy}>{busy ? 'Envoi…' : retryDocumentId ? 'Réessayer la création du CV' : 'Importer'}</Button>
      </form></Panel>
      <Panel title="Versions de mon CV">
        {!cvs.length ? <EmptyState title="Aucun CV importé">Importez votre premier CV avec le formulaire « Importer un CV ».</EmptyState> : <ul className="divide-y divide-line">{[...cvs].sort((a, b) => b.version_number - a.version_number).map((cv) => {
          const document = documents.find((item) => item.id === cv.document)
          return <li key={cv.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-4"><div><p className="font-medium text-navy">v{cv.version_number} — {cv.title} {cv.is_primary && <Badge tone="teal">Principal</Badge>}</p><p className="text-sm text-slate">{document?.file_name ?? 'Document'} · {formatDate(document?.uploaded_at)}</p></div><div className="flex flex-wrap gap-2">
            {document && <Button size="sm" variant="secondaire" disabled={busy} onClick={() => void action(() => download(document.id, document.file_name))}>Télécharger</Button>}
            {!cv.is_primary && <Button size="sm" variant="secondaire" disabled={busy} onClick={() => void action(() => setPrimary(cv))}>Définir principal</Button>}
            <Button size="sm" variant="danger" disabled={busy} onClick={() => setDeleting(cv)}>Supprimer</Button>
          </div></li>
        })}</ul>}
      </Panel>
      <AtsPanel cvs={cvs} onSaved={reload} />
      {deleting && (
        <ConfirmDialog
          title="Supprimer ce CV ?"
          danger
          onCancel={() => setDeleting(null)}
          onConfirm={() => { void action(() => deleteCV(deleting)); setDeleting(null) }}
        >
          La version v{deleting.version_number} — {deleting.title} sera supprimée.
        </ConfirmDialog>
      )}
    </PageBody>
  </>
}
