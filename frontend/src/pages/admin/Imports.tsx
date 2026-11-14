import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, ConfirmDialog, EmptyState, Field, Input, Modal, Panel, Row, Select, Table, Textarea } from '../../components/ui'
import { useBatches, useSources } from '../../state/adminData'
import * as api from '../../api/admin'
import { canLaunch, sourcePayload, type SourceForm } from '../../lib/adminSources'
import { IMPORT_BATCH_STATUS_LABEL, IMPORT_SOURCE_TYPE_LABEL, formatDateTime, labelFor } from '../../lib/format'

const EMPTY_SOURCE: SourceForm = { name: '', type: 'API', base_url: '', configuration: '' }
const EMPTY_AUTHORIZATION = { acquisition_method: '', permission_evidence: '', expires_at: '' }
const ACTIVE_BATCH = ['RUNNING', 'STARTED']
const REFRESH_MS = 10_000

export default function AdminImports() {
  const sources = useSources()
  const batches = useBatches()
  const [authorizing, setAuthorizing] = useState<string | null>(null)
  const [form, setForm] = useState(EMPTY_AUTHORIZATION)
  const [error, setError] = useState<string | null>(null)
  const [revoking, setRevoking] = useState<(typeof sources.data)[number] | null>(null)
  const [sourceDialog, setSourceDialog] = useState<{ source?: (typeof sources.data)[number] } | null>(null)
  const [launching, setLaunching] = useState<string | null>(null)
  const [notice, setNotice] = useState<string | null>(null)
  const running = batches.data.some((b) => ACTIVE_BATCH.includes(b.status))
  const runningFor = (sourceId: string) => batches.data.some((b) => b.source_id === sourceId && ACTIVE_BATCH.includes(b.status))

  // Un import dure plusieurs minutes : la liste des lots se rafraîchit tant qu’un lot est en cours.
  const { reload: reloadBatches } = batches
  useEffect(() => {
    if (!running) return
    const timer = window.setInterval(() => { void reloadBatches() }, REFRESH_MS)
    return () => window.clearInterval(timer)
  }, [running, reloadBatches])

  async function launch(source: (typeof sources.data)[number]) {
    setError(null); setNotice(null); setLaunching(source.id)
    try {
      await api.runImport(source.id)
      setNotice(`Import de ${source.name} lancé. Il tourne en arrière-plan ; la liste des lots se met à jour toute seule.`)
      await batches.reload()
    } catch (e) { setError(e instanceof Error ? e.message : 'Lancement refusé.') }
    finally { setLaunching(null) }
  }
  const set = (k: keyof typeof form) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })
  const sourceName = (id: string) => sources.data.find((s) => s.id === id)?.name ?? 'Source inconnue'

  // Chaque source part d’un formulaire vide : les valeurs de la source précédente ne restent pas.
  const startAuthorizing = (id: string) => { setForm(EMPTY_AUTHORIZATION); setError(null); setAuthorizing(authorizing === id ? null : id) }

  async function run(work: () => Promise<unknown>) {
    setError(null)
    try { await work(); setAuthorizing(null); await sources.reload() }
    catch (e) { setError(e instanceof Error ? e.message : 'Opération refusée.') }
  }

  return (
    <>
      <PageHeader title="Imports d’offres" />
      <PageBody className="space-y-6">
        {(error || sources.error || batches.error) && <p role="alert" className="text-coral">{error ?? sources.error ?? batches.error}</p>}
        {notice && <p role="status" className="text-[13px] text-teal-deep">{notice}</p>}
        <Panel
          title="Sources de données"
          action={<Button size="sm" onClick={() => setSourceDialog({})}>Déclarer une source</Button>}
        >
          {sources.loading ? <p className="p-5 text-slate">Chargement…</p> : sources.data.length === 0 ? (
            <EmptyState title="Aucune source déclarée" />
          ) : (
            <Table head={['Source', 'Type', 'Autorisation', '']}>
              {sources.data.map((s) => (
                <Row key={s.id}>
                  <Cell><span className="font-medium text-navy">{s.name}</span>{s.base_url && <p className="text-[12.5px] text-slate">{s.base_url}</p>}</Cell>
                  <Cell className="text-[13px]">{labelFor(IMPORT_SOURCE_TYPE_LABEL, s.type)}</Cell>
                  <Cell>
                    <Badge tone={s.is_authorized ? 'positif' : 'attention'}>{s.is_authorized ? 'Autorisée' : 'Non autorisée'}</Badge>
                    {s.expires_at && <p className="text-[12px] text-slate">jusqu’au {formatDateTime(s.expires_at)}</p>}
                  </Cell>
                  <Cell className="text-right">
                    {canLaunch(s) && (
                      <>
                        <Button size="sm" disabled={launching !== null || runningFor(s.id)} onClick={() => void launch(s)}>
                          {launching === s.id ? 'Lancement…' : runningFor(s.id) ? 'Import en cours' : 'Lancer l’import'}
                        </Button>{' '}
                      </>
                    )}
                    <Button size="sm" variant="discret" onClick={() => setSourceDialog({ source: s })}>Modifier</Button>{' '}
                    {s.is_authorized
                      ? <Button size="sm" variant="discret" onClick={() => setRevoking(s)}>Révoquer</Button>
                      : <Button size="sm" onClick={() => startAuthorizing(s.id)}>Autoriser</Button>}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
          {authorizing && (
            <div className="grid gap-4 border-t border-line p-5 sm:grid-cols-2">
              <p className="text-[13px] text-slate sm:col-span-2">Autorisation de : <span className="font-medium text-navy">{sourceName(authorizing)}</span></p>
              <Field label="Mode d’acquisition" required><Input value={form.acquisition_method} onChange={set('acquisition_method')} placeholder="Convention, API ouverte…" /></Field>
              <Field label="Valable jusqu’au" required><Input type="datetime-local" value={form.expires_at} onChange={set('expires_at')} /></Field>
              <div className="sm:col-span-2"><Field label="Preuve de l’autorisation" required><Input value={form.permission_evidence} onChange={set('permission_evidence')} /></Field></div>
              <div className="sm:col-span-2">
                <Button
                  disabled={!form.acquisition_method.trim() || !form.permission_evidence.trim() || !form.expires_at}
                  onClick={() => void run(() => api.authorizeSource(authorizing, { ...form, expires_at: new Date(form.expires_at).toISOString() }))}
                >
                  Valider l’autorisation
                </Button>
              </div>
            </div>
          )}
        </Panel>

        <Panel title="Lots d’import">
          {batches.loading && batches.data.length === 0 ? <p className="p-5 text-slate">Chargement…</p> : batches.data.length === 0 ? (
            <EmptyState title="Aucun import réalisé" />
          ) : (
            <Table head={['Source', 'Date', 'Ajoutées', 'Mises à jour', 'Inchangées', 'Rejetées', 'Statut']}>
              {batches.data.map((b) => (
                <Row key={b.id}>
                  <Cell className="text-[13px]"><Link to={`/admin/imports/batches/${b.id}`} className="font-medium text-navy hover:text-teal hover:underline">{sourceName(b.source_id)}</Link></Cell>
                  <Cell className="text-[13px] text-slate">{formatDateTime(b.started_at ?? b.created_at)}</Cell>
                  <Cell className="tnum text-[13px]">{b.added_count}</Cell>
                  <Cell className="tnum text-[13px]">{b.updated_count}</Cell>
                  <Cell className="tnum text-[13px]">{b.unchanged_count}</Cell>
                  <Cell className="tnum text-[13px]">{b.rejected_count}</Cell>
                  <Cell><Badge tone={b.status === 'COMPLETED' ? 'positif' : b.status === 'FAILED' ? 'negatif' : ACTIVE_BATCH.includes(b.status) ? 'encours' : 'neutre'}>{labelFor(IMPORT_BATCH_STATUS_LABEL, b.status)}</Badge></Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>
        {batches.hasMore && <div className="text-center"><Button variant="secondaire" disabled={batches.loading} onClick={() => void batches.loadMore()}>Charger plus</Button></div>}

        {sourceDialog && <SourceDialog source={sourceDialog.source} onClose={() => setSourceDialog(null)} onSaved={() => { setSourceDialog(null); void sources.reload() }} />}
        {revoking && (
          <ConfirmDialog
            title="Révoquer l’autorisation ?"
            danger
            onCancel={() => setRevoking(null)}
            onConfirm={() => { void run(() => api.revokeSource(revoking.id)); setRevoking(null) }}
          >
            La source {revoking.name} ne sera plus autorisée pour les imports. Vous pourrez l’autoriser de nouveau.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}

/** Déclarer une source (sans `source`) ou la modifier. */
function SourceDialog({ source, onClose, onSaved }: { source?: api.DataSource; onClose: () => void; onSaved: () => void }) {
  const [form, setForm] = useState<SourceForm>(source
    ? { name: source.name, type: source.type, base_url: source.base_url ?? '', configuration: source.configuration_json ? JSON.stringify(source.configuration_json, null, 2) : '' }
    : EMPTY_SOURCE)
  const [error, setError] = useState<string | null>(null)
  const set = (k: keyof SourceForm) => (e: { target: { value: string } }) => setForm({ ...form, [k]: e.target.value })

  async function save() {
    setError(null)
    const payload = sourcePayload(form)
    if (!payload.ok) { setError(payload.error); return }
    try {
      if (source) await api.updateSource(source.id, payload.body)
      else await api.createSource(payload.body)
      onSaved()
    } catch (e) { setError(e instanceof Error ? e.message : 'Enregistrement refusé.') }
  }

  return (
    <Modal
      open
      onClose={onClose}
      title={source ? 'Modifier la source' : 'Déclarer une source'}
      footer={
        <>
          <Button variant="secondaire" onClick={onClose}>Annuler</Button>
          <Button disabled={!form.name.trim()} onClick={() => void save()}>Enregistrer</Button>
        </>
      }
    >
      <div className="space-y-4">
        {error && <p role="alert" className="text-[13px] text-coral">{error}</p>}
        <Field label="Nom" required><Input value={form.name} onChange={set('name')} /></Field>
        <Field label="Type" required>
          <Select value={form.type} onChange={set('type')}>
            {Object.entries(IMPORT_SOURCE_TYPE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
          </Select>
        </Field>
        <Field label="URL de base" hint="Laisser vide pour une source sans adresse.">
          <Input value={form.base_url} onChange={set('base_url')} placeholder="https://" />
        </Field>
        <Field label="Configuration (JSON)" hint={'Facultatif. Collecte web : {"keywords": [""], "max_pages": 2} (mot-clé vide = toutes les offres). Changer keywords ou max_pages garde l’autorisation ; toute autre clé la retire.'}>
          <Textarea value={form.configuration} onChange={set('configuration')} className="font-mono text-[12.5px]" />
        </Field>
      </div>
    </Modal>
  )
}
