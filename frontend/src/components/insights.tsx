import { useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Button, Panel } from './ui'
import { ScoreDial, SkillChips } from './domain'
import { useCandidate } from '../state/candidate'
import { formatDate } from '../lib/format'
import { matchBadge } from '../lib/candidateOffers'

/** Runs the calculate action once per session on pages that show scores. */
export function useAutoMatches() {
  const { loading, autoCalculateMatches } = useCandidate()
  useEffect(() => autoCalculateMatches(), [loading])
}

/** Petit badge pour une carte d'offre ; rien n'est affiché si aucun score n'existe. */
export function MatchBadge({ offerId }: { offerId: string }) {
  const { matches } = useCandidate()
  const badge = matchBadge(matches.find((item) => item.offer_id === offerId))
  if (!badge) return null
  return <div className="mt-2 space-y-1.5 text-[12.5px]">
    <p className="font-medium text-teal">Compatibilité {badge.score} %</p>
    {badge.missing.length > 0 && <p className="flex flex-wrap items-center gap-1.5 text-slate">À acquérir : <SkillChips names={badge.missing} variant="missing" /></p>}
  </div>
}

/** Détail du score de matching sur la page d'une offre. */
export function MatchPanel({ offerId }: { offerId: string }) {
  const { matches, records, loading, calculating, scoresStale, calculateMatches } = useCandidate()
  useAutoMatches()
  const match = matches.find((item) => item.offer_id === offerId)
  if (loading) return null
  const hasSkills = records.skills.length > 0
  if (!match || match.overall_score === null) {
    return (
      <Panel title="Compatibilité avec votre profil">
        <div className="space-y-3 p-5 text-[13.5px] text-slate">
          {calculating ? <p role="status">Calcul de votre compatibilité…</p> : hasSkills ? (
            <>
              <p>Le score n’est pas encore calculé pour cette offre.</p>
              <Button size="sm" disabled={calculating} onClick={() => void calculateMatches().catch(() => {})}>Calculer ma compatibilité</Button>
            </>
          ) : (
            <p>Renseignez vos compétences pour obtenir un score. <Link to="/candidat/profil" className="font-medium text-teal">Ouvrir mon profil</Link></p>
          )}
        </div>
      </Panel>
    )
  }
  const matched = match.explanation_json?.matched_skills ?? []
  const missing = match.explanation_json?.missing_skills ?? []
  return (
    <Panel title="Compatibilité avec votre profil">
      <div className="flex flex-wrap items-start gap-6 p-5">
        <ScoreDial score={Math.round(Number(match.overall_score))} available size={72} />
        <div className="space-y-3 text-[13.5px]">
          {matched.length > 0 && <div><p className="mb-1.5 font-medium text-navy">Compétences en commun</p><SkillChips names={matched} variant="matched" /></div>}
          {missing.length > 0 && <div><p className="mb-1.5 font-medium text-navy">Compétences à acquérir</p><SkillChips names={missing} variant="missing" /></div>}
          <p className="text-[12px] text-slate">Calculé le {formatDate(match.calculated_at)}</p>
          {scoresStale && hasSkills && <Button size="sm" variant="secondaire" disabled={calculating} onClick={() => void calculateMatches().catch(() => {})}>Recalculer</Button>}
        </div>
      </div>
    </Panel>
  )
}
