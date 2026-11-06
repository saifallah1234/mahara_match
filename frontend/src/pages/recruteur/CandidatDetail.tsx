// Placement: frontend/src/pages/recruteur/CandidatDetail.tsx
import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { EmptyState, Note, Panel } from '../../components/ui'
import { useAuth } from '../../state/auth'
import { useRecruiter } from '../../state/recruiter'
import { getCandidate, listEducationLevels, type CandidateCard, type EducationLevel } from '../../api/recruiter'
import { ApiError } from '../../api/client'
import { SKILL_LEVEL_LABEL, WORK_MODE_LABEL, formatMonthYear, labelFor } from '../../lib/format'
import { RELOCATION_LABEL, UNVERIFIED_MESSAGE } from '../../lib/recruiterCandidates'

/** Read-only limited profile. No contact action: contact is not part of the MVP (D14). */
export default function RecruteurCandidatDetail() {
  const { candidateId } = useParams()
  const { workspace } = useAuth()
  const { skills } = useRecruiter()
  const verified = workspace?.organization?.verification_status === 'VERIFIED'
  const [card, setCard] = useState<CandidateCard | null>(null)
  const [levels, setLevels] = useState<EducationLevel[]>([])
  const [gone, setGone] = useState(false)
  const [loadError, setLoadError] = useState<string | null>(null)
  const [levelsError, setLevelsError] = useState<string | null>(null)

  useEffect(() => {
    if (!verified || !candidateId) return
    let live = true
    listEducationLevels()
      .then((rows) => { if (live) setLevels(rows) })
      .catch((failure) => { if (live) setLevelsError(failure instanceof Error ? failure.message : 'Niveaux de formation indisponibles.') })
    getCandidate(candidateId)
      .then((c) => { if (live) setCard(c) })
      .catch((e: unknown) => {
        if (!live) return
        // 404: the profile was made private or deactivated since the list was loaded.
        if (e instanceof ApiError && e.status === 404) setGone(true)
        else setLoadError(e instanceof Error ? e.message : 'Profil indisponible.')
      })
    return () => { live = false }
  }, [candidateId, verified])

  const skillName = (id: string) => skills.find((s) => s.id === id)?.canonical_name ?? 'Compétence'
  const levelName = (id: string) => levels.find((l) => l.id === id)?.name ?? 'Formation'

  return (
    <>
      <PageHeader back={{ to: '/recruteur/candidats', label: 'Candidats' }} title={card?.headline || 'Profil candidat'} description={card?.governorate} />
      <PageBody className="space-y-6">
        {!verified && <Note tone="attention">{UNVERIFIED_MESSAGE}</Note>}
        {verified && gone && <Note tone="attention">Ce profil n’est plus visible.</Note>}
        {verified && loadError && <p role="alert" className="text-coral">{loadError}</p>}
        {levelsError && <p role="alert" className="text-coral">{levelsError}</p>}
        {verified && !card && !gone && !loadError && <p className="text-slate">Chargement…</p>}
        {card && (
          <>
            <Panel title="Compétences">
              {card.skills.length === 0 ? (
                <EmptyState title="Aucune compétence renseignée." />
              ) : (
                <ul className="divide-y divide-line/70">
                  {card.skills.map((s) => (
                    <li key={s.skill} className="flex justify-between gap-3 px-5 py-3 text-[13.5px]">
                      <span className="text-navy">{skillName(s.skill)}</span>
                      <span className="text-slate">
                        {labelFor(SKILL_LEVEL_LABEL, s.level)}
                        {s.years_experience && ` · ${s.years_experience} an(s)`}
                      </span>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="Expériences">
              {card.experiences.length === 0 ? (
                <EmptyState title="Aucune expérience renseignée." />
              ) : (
                <ul className="divide-y divide-line/70">
                  {card.experiences.map((e, i) => (
                    <li key={i} className="px-5 py-3 text-[13.5px]">
                      <p className="font-medium text-navy">{e.job_title}</p>
                      <p className="text-slate">{e.organization_name} · {formatMonthYear(e.start_date)} – {formatMonthYear(e.end_date ?? undefined)}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="Formation">
              {card.educations.length === 0 ? (
                <EmptyState title="Aucune formation renseignée." />
              ) : (
                <ul className="divide-y divide-line/70">
                  {card.educations.map((e, i) => (
                    <li key={i} className="px-5 py-3 text-[13.5px]">
                      <p className="font-medium text-navy">{levelName(e.education_level)} · {e.field_of_study}</p>
                      <p className="text-slate">{e.institution} · {e.start_year} – {e.end_year ?? 'en cours'}</p>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>

            <Panel title="Préférences">
              <dl className="space-y-3 px-5 py-4 text-[13.5px]">
                <div><dt className="text-slate">Mode de travail</dt><dd className="text-navy">{labelFor(WORK_MODE_LABEL, card.preferences?.work_mode)}</dd></div>
                <div><dt className="text-slate">Mobilité</dt><dd className="text-navy">{labelFor(RELOCATION_LABEL, card.preferences?.relocation)}</dd></div>
                <div><dt className="text-slate">Distance maximale</dt><dd className="text-navy">{card.preferences?.distance ? `${card.preferences.distance} km` : '—'}</dd></div>
              </dl>
            </Panel>
          </>
        )}
      </PageBody>
    </>
  )
}
