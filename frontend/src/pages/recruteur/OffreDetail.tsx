import { useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Panel } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel } from '../../api/recruiter'
import { formatDate } from '../../lib/format'

const LABEL: Record<string, string> = {
  SUBMITTED: 'Soumise', UNDER_REVIEW: 'En examen', PRESELECTED: 'Présélectionnée', INTERVIEW: 'Entretien',
  OFFERED: 'Proposée', HIRED: 'Recrutée', REJECTED: 'Refusée', WITHDRAWN: 'Retirée',
}
const STATUS_LABEL = { PUBLISHED: 'Publiée', DRAFT: 'Brouillon', PAUSED: 'En pause', CLOSED: 'Clôturée', ARCHIVED: 'Archivée' } as const

export default function RecruteurOffreDetail() {
  const { offerId } = useParams()
  const { offers, applications, loading, setOfferStatus } = useRecruiter()
  const offer = offers.find((o) => o.id === offerId)

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
            <Badge tone={offer.status === 'PUBLISHED' ? 'positif' : 'neutre'}>{STATUS_LABEL[offer.status]}</Badge>
            {offer.status === 'DRAFT' && (
              <Button onClick={() => void setOfferStatus(offer.id, 'PUBLISHED').catch(() => {})}>Publier</Button>
            )}
            {offer.status === 'PUBLISHED' && (
              <Button variant="secondaire" onClick={() => void setOfferStatus(offer.id, 'CLOSED').catch(() => {})}>
                Clôturer l’offre
              </Button>
            )}
          </>
        }
      />
      <PageBody className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
          <Panel title="Description">
            <p className="max-w-[68ch] whitespace-pre-line px-5 py-4 text-[14px] leading-relaxed text-navy">{offer.description}</p>
          </Panel>
          <Panel title="Informations">
            <dl className="space-y-3 px-5 py-4 text-[13.5px]">
              <div><dt className="text-slate">Contrat</dt><dd className="text-navy">{offer.contract_type || '—'}</dd></div>
              <div><dt className="text-slate">Mode de travail</dt><dd className="text-navy">{offer.work_mode || '—'}</dd></div>
              <div><dt className="text-slate">Expérience</dt><dd className="text-navy">{offer.experience_level || '—'}</dd></div>
              <div><dt className="text-slate">Salaire</dt><dd className="text-navy">{salary}</dd></div>
              <div><dt className="text-slate">Date limite</dt><dd className="text-navy">{offer.application_deadline ? formatDate(offer.application_deadline) : '—'}</dd></div>
              <div><dt className="text-slate">Candidature</dt><dd className="text-navy">{offer.easy_apply ? 'Sur la plateforme' : 'Sur le site de l’employeur'}</dd></div>
            </dl>
          </Panel>
        </div>

        <Panel title={`Candidatures reçues (${received.length})`}>
          {received.length === 0 ? (
            <p className="px-5 py-4 text-[13.5px] text-slate">Aucune candidature pour cette offre.</p>
          ) : (
            <ul className="divide-y divide-line/70">
              {received.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13.5px] text-navy">{candidateLabel(a)} · {formatDate(a.applied_at)}</span>
                  <Badge tone="neutre">{LABEL[a.status] ?? a.status}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Panel>
      </PageBody>
    </>
  )
}