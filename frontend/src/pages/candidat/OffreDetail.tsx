import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, Field, Panel, Select, Textarea } from '../../components/ui'
import { useCandidate } from '../../state/candidate'
import { CONTRACT_LABEL, EXPERIENCE_LABEL, WORK_MODE_LABEL, formatDate } from '../../lib/format'
import type { ContractType, ExperienceLevel, WorkMode } from '../../lib/types'

export default function CandidatOffreDetail() {
  const { offerId } = useParams()
  const navigate = useNavigate()
  const { offers, cvs, applications, apply } = useCandidate()
  const [cvId, setCvId] = useState('')
  const [letter, setLetter] = useState('')
  const [busy, setBusy] = useState(false)
  const offer = offers.find((item) => item.id === offerId)
  if (!offer) return <PageBody><Panel className="p-5">Offre introuvable ou fermée.</Panel></PageBody>
  const applied = applications.some((item) => item.offer_id === offer.id)
  const expired = !!offer.application_deadline && offer.application_deadline < new Date().toISOString().slice(0, 10)
  async function submit(event: React.FormEvent) {
    event.preventDefault(); setBusy(true)
    try { await apply(offer!.id, cvId, letter); navigate('/candidat/candidatures') }
    catch { /* The workspace shows the API error. */ }
    finally { setBusy(false) }
  }
  return <>
    <PageHeader back={{ to: '/candidat/offres', label: 'Toutes les offres' }} title={offer.title} description={`${offer.organization_name} · ${offer.city || offer.governorate}`} />
    <PageBody className="space-y-5">
      <Panel title="Description"><p className="whitespace-pre-wrap p-5 text-sm text-navy">{offer.description}</p></Panel>
      <Panel title="Informations"><dl className="grid gap-2 p-5 text-sm"><div>Contrat : {CONTRACT_LABEL[offer.contract_type as ContractType] || offer.contract_type || 'Non renseigné'}</div><div>Mode : {WORK_MODE_LABEL[offer.work_mode as WorkMode] || offer.work_mode || 'Non renseigné'}</div><div>Expérience : {EXPERIENCE_LABEL[offer.experience_level as ExperienceLevel] || offer.experience_level || 'Non renseignée'}</div><div>Clôture : {formatDate(offer.application_deadline ?? undefined)}</div></dl></Panel>
      {applied ? <Panel className="p-5">Vous avez déjà postulé à cette offre. <Link className="text-teal underline" to="/candidat/candidatures">Voir la candidature</Link></Panel>
        : offer.easy_apply ? <Panel title="Postuler"><form onSubmit={(event) => void submit(event)} className="space-y-4 p-5">
          <Field label="CV à transmettre" required><Select required value={cvId} onChange={(event) => setCvId(event.target.value)}><option value="">{cvs.length ? 'Choisir un CV' : 'Importez d’abord un CV'}</option>{cvs.map((cv) => <option key={cv.id} value={cv.id}>v{cv.version_number} — {cv.title}</option>)}</Select></Field>
          {!cvs.length && <Link className="text-teal underline" to="/candidat/cv">Importer un CV</Link>}
          <Field label="Message de candidature"><Textarea value={letter} onChange={(event) => setLetter(event.target.value)} /></Field>
          <Button type="submit" disabled={!cvs.length || expired || busy}>{busy ? 'Envoi…' : 'Déposer ma candidature'}</Button>{expired && <p className="text-coral">La date limite est passée.</p>}
        </form></Panel> : <Panel className="p-5">Candidature sur le site de l’employeur. {offer.offer_url && <a className="text-teal underline" href={offer.offer_url} target="_blank" rel="noreferrer">Ouvrir le site</a>}</Panel>}
    </PageBody>
  </>
}
