import { useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Field, Modal, Note, Panel, Select, Textarea } from '../../components/ui'
import { MatchLedger, StatusPill } from '../../components/domain'
import { useStore } from '../../state/store'
import { computeMatch } from '../../lib/matching'
import { CONTRACT_LABEL, EXPERIENCE_LABEL, OFFER_STATUS_LABEL, WORK_MODE_LABEL, formatDate, formatPlace, formatSalary } from '../../lib/format'
import { EDUCATION_LEVELS } from '../../data/referentials'

export default function CandidatOffreDetail() {
  const { offerId } = useParams()
  const navigate = useNavigate()
  const { currentProfile, offerOf, organizationOf, skills, cvs, applications, apply, programs } = useStore()
  const [applyOpen, setApplyOpen] = useState(false)
  const [cvId, setCvId] = useState('')
  const [letter, setLetter] = useState('')

  const offer = offerId ? offerOf(offerId) : undefined
  if (!offer || !currentProfile) {
    return (
      <PageBody>
        <Panel className="p-8">
          <p className="text-center text-[14px] text-slate">Cette offre est introuvable.</p>
        </Panel>
      </PageBody>
    )
  }

  const organization = organizationOf(offer.organizationId)
  const parent = organizationOf(organization?.parentId)
  const match = computeMatch(currentProfile, offer, skills)
  const myCVs = cvs.filter((c) => c.candidateId === currentProfile.id).sort((a, b) => b.versionNumber - a.versionNumber)
  const existing = applications.find(
    (a) => a.offerId === offer.id && a.candidateId === currentProfile.id && a.status !== 'WITHDRAWN',
  )

  const closed = offer.status !== 'PUBLISHED'
  const deadlinePassed = offer.applicationDeadline ? new Date(offer.applicationDeadline) < new Date() : false

  const relatedTrainings = programs.filter(
    (p) => p.status === 'PUBLISHED' && p.skillIds.some((id) => match.missingSkillIds.includes(id)),
  )

  function submit() {
    const result = apply(offer!.id, cvId || myCVs[0]?.id, letter)
    if (result.ok) {
      setApplyOpen(false)
      navigate('/candidat/candidatures')
    }
  }

  return (
    <>
      <PageHeader
        back={{ to: '/candidat/offres', label: 'Toutes les offres' }}
        title={offer.title}
        description={
          <>
            {organization?.legalName}
            {parent && ` — ${parent.legalName}`} · {formatPlace(offer.city, offer.governorate)}
          </>
        }
        action={
          existing ? (
            <div className="flex items-center gap-2">
              <span className="text-[13px] text-slate">Déjà candidatée :</span>
              <StatusPill status={existing.status} />
            </div>
          ) : closed ? (
            <Badge tone="negatif">{OFFER_STATUS_LABEL[offer.status]}</Badge>
          ) : !offer.easyApply ? (
            <a href={offer.externalUrl} target="_blank" rel="noreferrer">
              <Button variant="secondaire">Postuler sur le site de l’employeur</Button>
            </a>
          ) : (
            <Button onClick={() => setApplyOpen(true)} disabled={deadlinePassed}>
              Postuler
            </Button>
          )
        }
      />

      <PageBody className="space-y-6">
        {closed && (
          <Note tone="danger">
            Cette offre n’est plus ouverte. Le dépôt de candidature est refusé, même si la page était déjà affichée.
          </Note>
        )}

        {!closed && deadlinePassed && (
          <Note tone="danger">La date limite de candidature est dépassée. Le dépôt n’est plus possible.</Note>
        )}

        {!offer.easyApply && !closed && (
          <Note tone="attention">
            Cette offre se dépose sur le site de l’employeur. Le suivi de la candidature et des entretiens n’est pas
            disponible pour ce type de dépôt.
          </Note>
        )}

        <div className="grid gap-6 lg:grid-cols-[1fr_380px] lg:items-start">
          <div className="space-y-6">
            <Panel title="Pourquoi cette offre vous correspond">
              <div className="p-5">
                <MatchLedger match={match} />
              </div>
            </Panel>

            <Panel title="Description du poste">
              <div className="px-5 py-4">
                <p className="max-w-[68ch] text-[14px] leading-relaxed text-navy">{offer.description}</p>
              </div>
            </Panel>

            {match.missingSkillIds.length > 0 && (
              <Panel
                title="Combler les écarts"
              >
                {relatedTrainings.length === 0 ? (
                  <p className="px-5 py-4 text-[13.5px] text-slate">
                    Aucune formation correspondante n’a été trouvée dans le catalogue pour ces compétences.
                  </p>
                ) : (
                  <ul className="divide-y divide-line/70">
                    {relatedTrainings.map((program) => (
                      <li key={program.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                        <div className="min-w-0">
                          <p className="text-[14px] font-medium text-navy">{program.title}</p>
                          <p className="text-[12.5px] text-slate">
                            {organizationOf(program.organizationId)?.legalName} · {program.durationHours} h
                          </p>
                        </div>
                        <Link to="/candidat/formations">
                          <Button size="sm" variant="secondaire">
                            Voir la formation
                          </Button>
                        </Link>
                      </li>
                    ))}
                  </ul>
                )}
              </Panel>
            )}
          </div>

          <div className="space-y-4">
            <Panel title="Informations">
              <dl className="divide-y divide-line/70 text-[13.5px]">
                {[
                  ['Référence', offer.reference],
                  ['Contrat', CONTRACT_LABEL[offer.contractType]],
                  ['Mode de travail', WORK_MODE_LABEL[offer.workMode]],
                  ['Expérience attendue', EXPERIENCE_LABEL[offer.experienceLevel]],
                  ['Niveau d’études', EDUCATION_LEVELS.find((l) => l.id === offer.educationLevelId)?.name ?? 'Non renseigné'],
                  ['Rémunération', formatSalary(offer.minSalary, offer.maxSalary)],
                  ['Publiée le', formatDate(offer.publishedAt)],
                  ['Clôture', offer.applicationDeadline ? formatDate(offer.applicationDeadline) : 'Non renseignée'],
                ].map(([label, value]) => (
                  <div key={label} className="flex items-baseline justify-between gap-4 px-5 py-2.5">
                    <dt className="shrink-0 text-slate">{label}</dt>
                    <dd className="text-right font-medium text-navy">{value}</dd>
                  </div>
                ))}
              </dl>
            </Panel>

            <Panel title="Votre situation géographique">
              <div className="space-y-2 px-5 py-4 text-[13.5px]">
                <p className={match.sameGovernorate ? 'text-navy' : 'text-slate'}>
                  {match.sameGovernorate
                    ? `Même gouvernorat que vous (${offer.governorate}).`
                    : `Offre à ${offer.governorate}, vous êtes à ${currentProfile.governorate}.`}
                </p>
                <p className={match.workModeCompatible ? 'text-navy' : 'text-coral'}>
                  {match.workModeCompatible
                    ? 'Le mode de travail est compatible avec vos préférences.'
                    : 'Le mode de travail ne correspond pas à vos préférences actuelles.'}
                </p>
                <p className="text-[12.5px] leading-relaxed text-slate">
                  Ces éléments sont affichés à titre de contexte. Ils n’entrent pas dans le score de couverture.
                </p>
              </div>
            </Panel>
          </div>
        </div>
      </PageBody>

      <Modal
        open={applyOpen}
        onClose={() => setApplyOpen(false)}
        title="Postuler à cette offre"
        footer={
          <>
            <Button variant="secondaire" onClick={() => setApplyOpen(false)}>
              Annuler
            </Button>
            <Button onClick={submit}>Confirmer le dépôt</Button>
          </>
        }
      >
        <div className="space-y-4">
          <div className="rounded-[8px] border border-line bg-mist/50 px-4 py-3 text-[13px]">
            <p className="font-medium text-navy">{offer.title}</p>
            <p className="text-slate">
              {organization?.legalName} · {formatPlace(offer.city, offer.governorate)}
            </p>
          </div>

          <Field
            label="Version de CV à transmettre"
            required
            hint="Cette version sera figée dans votre dossier, même si vous modifiez votre profil ensuite."
          >
            <Select value={cvId} onChange={(e) => setCvId(e.target.value)}>
              {myCVs.map((cv) => (
                <option key={cv.id} value={cv.id}>
                  v{cv.versionNumber} — {cv.title}
                  {cv.isPrimary ? ' (principal)' : ''}
                </option>
              ))}
            </Select>
          </Field>

          <Field label="Message de candidature" hint="Facultatif. L’assistant peut en préparer un à partir de vos expériences confirmées.">
            <Textarea
              value={letter}
              onChange={(e) => setLetter(e.target.value)}
              rows={5}
              placeholder="Quelques lignes sur ce qui vous rapproche de ce poste…"
            />
          </Field>
        </div>
      </Modal>
    </>
  )
}
