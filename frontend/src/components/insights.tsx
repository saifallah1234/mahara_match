import { Link } from 'react-router-dom'
import { Button, Panel } from './ui'
import { ScoreDial } from './domain'
import { useCandidate } from '../state/candidate'
import { formatDate, skillLabel } from '../lib/format'

/** Petit badge pour une carte d'offre ; rien n'est affiché si aucun score n'existe. */
export function MatchBadge({ offerId }: { offerId: string }) {
  const { matches } = useCandidate()
  const match = matches.find((item) => item.offer_id === offerId)
  if (!match || match.overall_score === null) return null
  return <p className="mt-2 text-[12.5px] font-medium text-teal">Compatibilité {Math.round(Number(match.overall_score))} %</p>
}

/** Détail du score de matching sur la page d'une offre. */
export function MatchPanel({ offerId }: { offerId: string }) {
  const { matches, records, loading, calculating, scoresStale, calculateMatches } = useCandidate()
  const match = matches.find((item) => item.offer_id === offerId)
  if (loading) return null
  const hasSkills = records.skills.length > 0
  if (!match || match.overall_score === null) {
    return (
      <Panel title="Compatibilité avec votre profil">
        <div className="space-y-3 p-5 text-[13.5px] text-slate">
          {hasSkills ? (
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
          {matched.length > 0 && <p><span className="font-medium text-navy">Compétences en commun : </span>{matched.map(skillLabel).join(', ')}</p>}
          {missing.length > 0 && <p><span className="font-medium text-navy">Compétences à acquérir : </span>{missing.map(skillLabel).join(', ')}</p>}
          <p className="text-[12px] text-slate">Calculé le {formatDate(match.calculated_at)}</p>
          {scoresStale && hasSkills && <Button size="sm" variant="secondaire" disabled={calculating} onClick={() => void calculateMatches().catch(() => {})}>Recalculer</Button>}
        </div>
      </div>
    </Panel>
  )
}
