import { useState } from 'react'
import { useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Panel } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel } from '../../api/recruiter'
import { OFFER_STATUS_LABEL, WORK_MODE_LABEL, contractLabel, experienceLabel, formatDate, labelFor } from '../../lib/format'
import { STATUS_LABEL } from '../../lib/statusMachine'
import type { WorkMode } from '../../lib/types'

export default function RecruteurOffreDetail() {
  const { offerId } = useParams()
  const { offers, applications, loading, error, setOfferStatus } = useRecruiter()
  const offer = offers.find((o) => o.id === offerId)
  const [closing, setClosing] = useState(false)

  if (loading && !offer) return <PageBody><p className="text-slate">Chargement…</p></PageBody>
  if (!offer) {
    return (
      <PageBody>
        <Panel className="p-8"><p className="text-center text-[14px] text-slate">Cette offre est introuvable.</p></Panel>
      </PageBody>
    )
  }

  const received = applications.filter((a) => a.offer_id === offer.id)
  const salary = offer.min_salary || offer.max_salary
    ? `${offer.min_salary ?? '…'} – ${offer.max_salary ?? '…'} TND`
    : 'Non renseigné'

  return (
    <>
      <PageHeader
        back={{ to: '/recruteur/offres', label: 'Mes offres' }}
        title={offer.title}
        description={`${offer.organization_name} · ${offer.city || offer.governorate}`}
        action={
          <>
            <Badge tone={offer.status === 'PUBLISHED' ? 'positif' : 'neutre'}>{OFFER_STATUS_LABEL[offer.status]}</Badge>
            {offer.status === 'DRAFT' && (
              <Button onClick={() => void setOfferStatus(offer.id, 'PUBLISHED').catch(() => {})}>Publier</Button>
            )}
            {offer.status === 'PUBLISHED' && (
              <Button variant="secondaire" onClick={() => setClosing(true)}>
                Clôturer l’offre
              </Button>
            )}
          </>
        }
      />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        <div className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
          <Panel title="Description">
            <p className="max-w-[68ch] whitespace-pre-line px-5 py-4 text-[14px] leading-relaxed text-navy">{offer.description}</p>
          </Panel>
          <Panel title="Informations">
            <dl className="space-y-3 px-5 py-4 text-[13.5px]">
              <div><dt className="text-slate">Contrat</dt><dd className="text-navy">{contractLabel(offer.contract_type)}</dd></div>
              <div><dt className="text-slate">Mode de travail</dt><dd className="text-navy">{WORK_MODE_LABEL[offer.work_mode as WorkMode] ?? '—'}</dd></div>
              <div><dt className="text-slate">Expérience</dt><dd className="text-navy">{experienceLabel(offer.experience_level)}</dd></div>
              <div><dt className="text-slate">Salaire</dt><dd className="text-navy">{salary}</dd></div>
              <div><dt className="text-slate">Date limite</dt><dd className="text-navy">{offer.application_deadline ? formatDate(offer.application_deadline) : '—'}</dd></div>
              <div><dt className="text-slate">Candidature</dt><dd className="text-navy">{offer.easy_apply ? 'Sur la plateforme' : 'Sur le site de l’employeur'}</dd></div>
            </dl>
          </Panel>
        </div>

        <Panel title={`Candidatures reçues (${received.length})`}>
          {received.length === 0 ? (
            <EmptyState title="Aucune candidature pour cette offre." />
          ) : (
            <ul className="divide-y divide-line/70">
              {received.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13.5px] text-navy">{candidateLabel(a)} · {formatDate(a.applied_at)}</span>
                  <Badge tone="neutre">{labelFor(STATUS_LABEL, a.status)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        {closing && (
          <ConfirmDialog
            title="Clôturer cette offre ?"
            danger
            onCancel={() => setClosing(false)}
            onConfirm={() => { void setOfferStatus(offer.id, 'CLOSED').catch(() => {}); setClosing(false) }}
          >
            L’offre « {offer.title} » ne sera plus ouverte aux candidatures.
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}