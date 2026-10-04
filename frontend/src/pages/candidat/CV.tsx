import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, EmptyState, Field, Modal, Note, Panel, Select, Table, Row, Cell, Meter } from '../../components/ui'
import { ProvenanceRow } from '../../components/domain'
import { useStore } from '../../state/store'
import { parseCV } from '../../api/client'
import { EXTRACTED_FIELDS } from '../../data/seed'
import { formatBytes, formatDate } from '../../lib/format'
import type { ExtractedField } from '../../lib/types'

type Mode = 'liste' | 'import' | 'diagnostic'

export default function CandidatCV() {
  const { currentProfile, cvs, analyses, offers, organizationOf } = useStore()
  const [mode, setMode] = useState<Mode>('liste')
  const [fields, setFields] = useState<ExtractedField[]>(EXTRACTED_FIELDS)
  const [parsing, setParsing] = useState<{ fileName: string; ocrUsed: boolean; pageCount: number } | null>(null)
  const [busy, setBusy] = useState(false)
  const [generateOpen, setGenerateOpen] = useState(false)
  const [targetOffer, setTargetOffer] = useState('')

  if (!currentProfile) return null

  const mine = cvs.filter((c) => c.candidateId === currentProfile.id).sort((a, b) => b.versionNumber - a.versionNumber)
  const analysis = analyses[0]
  const settled = fields.filter((f) => f.status !== 'PROPOSED').length
  const openOffers = offers.filter((o) => o.status === 'PUBLISHED')

  async function startImport(fileName: string) {
    setBusy(true)
    setMode('import')
    const result = await parseCV(fileName)
    setParsing({ fileName, ...result })
    setFields(EXTRACTED_FIELDS.map((f) => ({ ...f })))
    setBusy(false)
  }

  return (
    <>
      <PageHeader
        title="Mes CV"
        action={
          mode === 'liste' ? (
            <>
              <Button variant="secondaire" onClick={() => setGenerateOpen(true)}>
                Générer un CV ciblé
              </Button>
              <Button onClick={() => startImport('CV_scan_octobre.jpg')}>Importer un CV</Button>
            </>
          ) : (
            <Button variant="secondaire" onClick={() => setMode('liste')}>
              Retour à mes CV
            </Button>
          )
        }
      />

      <PageBody className="space-y-6">
        {mode === 'liste' && (
          <>
            <Panel title="Versions de mon CV">
              {mine.length === 0 ? (
                <EmptyState title="Aucun CV importé" action={<Button onClick={() => startImport('cv.pdf')}>Importer un CV</Button>}>
                  Importez un PDF, un scan ou une photo. La plateforme en extrait les informations que vous confirmerez ensuite.
                </EmptyState>
              ) : (
                <Table head={['Version', 'Fichier', 'Importé le', 'Lecture', '']}>
                  {mine.map((cv) => (
                    <Row key={cv.id}>
                      <Cell>
                        <div className="flex items-center gap-2">
                          <span className="font-medium text-navy">v{cv.versionNumber}</span>
                          {cv.isPrimary && <Badge tone="teal">Principal</Badge>}
                        </div>
                        <p className="text-[12.5px] text-slate">{cv.title}</p>
                      </Cell>
                      <Cell>
                        <p className="text-[13px] text-navy">{cv.fileName}</p>
                        <p className="text-[12.5px] text-slate">
                          {formatBytes(cv.sizeBytes)} · {cv.pageCount} page{cv.pageCount > 1 ? 's' : ''}
                        </p>
                      </Cell>
                      <Cell className="text-[13px] text-slate">{formatDate(cv.uploadedAt)}</Cell>
                      <Cell>
                        {cv.ocrUsed ? <Badge tone="attention">OCR utilisé</Badge> : <Badge tone="positif">Texte natif</Badge>}
                      </Cell>
                      <Cell className="text-right">
                        <Button size="sm" variant="discret" onClick={() => setMode('diagnostic')}>
                          Diagnostic ATS
                        </Button>
                      </Cell>
                    </Row>
                  ))}
                </Table>
              )}
            </Panel>

          </>
        )}

        {mode === 'import' && (
          <>
            {busy && (
              <Panel className="p-8">
                <p className="text-center text-[14px] text-slate">Lecture du document en cours…</p>
              </Panel>
            )}

            {!busy && parsing && (
              <>
                <Panel className="p-5">
                  <div className="flex flex-wrap items-center justify-between gap-4">
                    <div>
                      <p className="text-[15px] font-semibold text-navy">{parsing.fileName}</p>
                      <p className="mt-0.5 text-[13px] text-slate">
                        {parsing.pageCount} page{parsing.pageCount > 1 ? 's' : ''} ·{' '}
                        {parsing.ocrUsed
                          ? 'aucun texte exploitable détecté, le document est passé par la reconnaissance optique'
                          : 'texte extrait directement du PDF'}
                      </p>
                    </div>
                    {parsing.ocrUsed ? <Badge tone="attention">OCR</Badge> : <Badge tone="positif">Texte natif</Badge>}
                  </div>
                  <div className="mt-4 max-w-sm">
                    <Meter value={Math.round((settled / fields.length) * 100)} label={`${settled} champ sur ${fields.length} traité${settled > 1 ? 's' : ''}`} />
                  </div>
                </Panel>

                <Note tone="attention">
                  Les champs signalés comme lecture incertaine méritent un coup d’œil : la reconnaissance peut avoir mal
                  lu une date ou un chiffre. Corrigez directement dans le champ, puis confirmez.
                </Note>

                <Panel
                  title="Informations proposées"
                  action={
                    <Button
                      size="sm"
                      variant="secondaire"
                      onClick={() => setFields((list) => list.map((f) => (f.status === 'PROPOSED' ? { ...f, status: 'CONFIRMED' } : f)))}
                    >
                      Tout confirmer
                    </Button>
                  }
                >
                  <ul className="divide-y divide-line/70">
                    {fields.map((field) => (
                      <ProvenanceRow
                        key={field.id}
                        field={field}
                        onConfirm={() =>
                          setFields((list) => list.map((f) => (f.id === field.id ? { ...f, status: 'CONFIRMED' } : f)))
                        }
                        onCorrect={(value) =>
                          setFields((list) =>
                            list.map((f) => (f.id === field.id ? { ...f, status: 'CORRECTED', correctedValue: value } : f)),
                          )
                        }
                      />
                    ))}
                  </ul>
                  <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line px-5 py-3.5">
                    <p className="text-[12.5px] text-slate">
                      Vos corrections sont conservées : un nouvel import proposera des modifications sans les écraser.
                    </p>
                    <Button disabled={settled < fields.length} onClick={() => setMode('liste')}>
                      {settled < fields.length ? `${fields.length - settled} champ(s) à traiter` : 'Enregistrer dans mon profil'}
                    </Button>
                  </div>
                </Panel>
              </>
            )}
          </>
        )}

        {mode === 'diagnostic' && analysis && (
          <>
            <Panel className="p-5">
              <div className="flex flex-wrap items-center justify-between gap-4">
                <div>
                  <p className="text-[15px] font-semibold text-navy">Diagnostic ATS</p>
                  <p className="mt-0.5 text-[13px] text-slate">Analysé le {formatDate(analysis.analyzedAt)}</p>
                </div>
                <div className="w-full max-w-xs">
                  <Meter
                    value={analysis.overallScore}
                    label="Contrôles réussis"
                    tone={analysis.overallScore >= 70 ? 'teal' : 'amber'}
                  />
                </div>
              </div>
            </Panel>

            <Panel title="Contrôles réalisés">
              <ul className="divide-y divide-line/70">
                {analysis.checks.map((check) => (
                  <li key={check.code} className="flex gap-3 px-5 py-3.5">
                    <span
                      aria-hidden
                      className={`mt-1 flex h-5 w-5 shrink-0 items-center justify-center rounded-full ${check.passed ? 'bg-leaf/12 text-leaf' : 'bg-amber/15 text-[#946019]'}`}
                    >
                      <svg width="11" height="11" viewBox="0 0 16 16" fill="none">
                        {check.passed ? (
                          <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                        ) : (
                          <path d="M8 4v5M8 11.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
                        )}
                      </svg>
                    </span>
                    <div>
                      <p className="text-[14px] font-medium text-navy">{check.label}</p>
                      <p className="mt-0.5 text-[13px] leading-relaxed text-slate">{check.detail}</p>
                    </div>
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel title="Suggestions">
              <ul className="space-y-2 px-5 py-4">
                {analysis.suggestions.map((suggestion) => (
                  <li key={suggestion} className="flex gap-2.5 text-[13.5px] text-navy">
                    <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-teal" />
                    {suggestion}
                  </li>
                ))}
              </ul>
            </Panel>
          </>
        )}
      </PageBody>

      <Modal
        open={generateOpen}
        onClose={() => setGenerateOpen(false)}
        title="Générer un CV ciblé"
        footer={
          <>
            <Button variant="secondaire" onClick={() => setGenerateOpen(false)}>
              Annuler
            </Button>
            <Button disabled={!targetOffer} onClick={() => setGenerateOpen(false)}>
              Générer le CV
            </Button>
          </>
        }
      >
        <Field label="Offre visée" required hint="Le CV met en avant les éléments confirmés qui répondent aux compétences de cette offre.">
          <Select value={targetOffer} onChange={(e) => setTargetOffer(e.target.value)}>
            <option value="">Choisir une offre</option>
            {openOffers.map((offer) => (
              <option key={offer.id} value={offer.id}>
                {offer.title} — {organizationOf(offer.organizationId)?.legalName}
              </option>
            ))}
          </Select>
        </Field>
      </Modal>
    </>
  )
}
