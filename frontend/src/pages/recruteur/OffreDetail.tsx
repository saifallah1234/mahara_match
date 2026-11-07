import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, ConfirmDialog, EmptyState, Loading, Panel } from '../../components/ui'
import { useRecruiter } from '../../state/recruiter'
import { candidateLabel, listOfferSkills, type OfferSkill } from '../../api/recruiter'
import { OFFER_STATUS_LABEL, WORK_MODE_LABEL, contractLabel, experienceLabel, formatDate, labelFor, skillLabel } from '../../lib/format'
import { STATUS_LABEL } from '../../lib/statusMachine'
import { offerActions, type OfferAction } from '../../lib/offerLifecycle'
import type { WorkMode } from '../../lib/types'

export default function RecruteurOffreDetail() {
  const { offerId } = useParams()
  const notice = (useLocation().state as { notice?: string } | null)?.notice
  const { offers, applications, skills, loading, error, setOfferStatus } = useRecruiter()
  const [pending, setPending] = useState<OfferAction | null>(null)
  const [offerSkills, setOfferSkills] = useState<OfferSkill[]>([])
  const [skillsError, setSkillsError] = useState<string | null>(null)
  const offer = offers.find((o) => o.id === offerId)

  useEffect(() => {
    if (!offerId) return
    let live = true
    listOfferSkills(offerId)
      .then((rows) => { if (live) setOfferSkills(rows) })
      .catch((failure) => { if (live) setSkillsError(failure instanceof Error ? failure.message : 'Compétences indisponibles.') })
    return () => { live = false }
  }, [offerId])

  if (loading && !offer) return <PageBody><Loading /></PageBody>
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
  const skillName = (id: string) => skillLabel(skills.find((s) => s.id === id)?.canonical_name ?? 'Compétence')

  return (
    <>
      <PageHeader
        back={{ to: '/recruteur/offres', label: 'Mes offres' }}
        title={offer.title}
        description={`${offer.organization_name} · ${offer.city || offer.governorate}`}
        action={
          <>
            <Badge tone={offer.status === 'PUBLISHED' ? 'positif' : 'neutre'}>{OFFER_STATUS_LABEL[offer.status]}</Badge>
            {offer.status !== 'ARCHIVED' && (
              <Link to={`/recruteur/offres/${offer.id}/modifier`}><Button variant="secondaire">Modifier</Button></Link>
            )}
            {offerActions(offer.status).map((action) => (
              <Button
                key={action.to}
                variant={action.confirm ? 'secondaire' : 'primaire'}
                onClick={() => (action.confirm ? setPending(action) : void setOfferStatus(offer.id, action.to).catch(() => {}))}
              >
                {action.label}
              </Button>
            ))}
          </>
        }
      />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {notice && <p role="alert" className="text-coral">{notice}</p>}
        {skillsError && <p role="alert" className="text-coral">{skillsError}</p>}
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
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

        <Panel title={`Compétences (${offerSkills.length})`}>
          {offerSkills.length === 0 ? (
            <EmptyState title="Aucune compétence." action={<Link to={`/recruteur/offres/${offer.id}/modifier`}><Button size="sm" variant="secondaire">Ajouter des compétences</Button></Link>}>Les compétences servent à calculer la compatibilité des candidats.</EmptyState>
          ) : (
            <ul className="divide-y divide-line/70">
              {offerSkills.map((s) => (
                <li key={s.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13.5px] text-navy">{skillName(s.skill_id)}</span>
                  <Badge tone={s.is_mandatory ? 'attention' : 'neutre'}>{s.is_mandatory ? 'Obligatoire' : 'Souhaitée'}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Panel>

        <Panel
          title={`Candidatures reçues (${received.length})`}
          action={<Link to={`/recruteur/candidatures?offer=${offer.id}`} className="text-[13px] font-medium text-teal hover:underline">Voir le suivi</Link>}
        >
          {received.length === 0 ? (
            <EmptyState title="Aucune candidature pour cette offre.">Les candidatures apparaîtront ici dès leur dépôt.</EmptyState>
          ) : (
            <ul className="divide-y divide-line/70">
              {received.map((a) => (
                <li key={a.id} className="flex items-center justify-between gap-3 px-5 py-3">
                  <span className="text-[13.5px] text-navy">{candidateLabel(a)} · {a.applicant.email} · {formatDate(a.applied_at)}</span>
                  <Badge tone="neutre">{labelFor(STATUS_LABEL, a.status)}</Badge>
                </li>
              ))}
            </ul>
          )}
        </Panel>
        {pending && (
          <ConfirmDialog
            title={`${pending.label} ?`}
            danger={pending.to === 'CLOSED' || pending.to === 'ARCHIVED'}
            onCancel={() => setPending(null)}
            onConfirm={() => { void setOfferStatus(offer.id, pending.to).catch(() => {}); setPending(null) }}
          >
            L’offre « {offer.title} » passera au statut « {OFFER_STATUS_LABEL[pending.to]} ».
          </ConfirmDialog>
        )}
      </PageBody>
    </>
  )
}
