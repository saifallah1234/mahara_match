import { Panel } from './ui'
import { ScoreDial } from './domain'
import { useOfferMatches } from '../state/insights'
import { formatDate } from '../lib/format'

/** Petit badge pour une carte d'offre ; rien n'est affiché si aucun score n'existe. */
export function MatchBadge({ offerId }: { offerId: string }) {
  const { byOffer } = useOfferMatches()
  const match = byOffer.get(offerId)
  if (!match || match.overall_score === null) return null
  return <p className="mt-2 text-[12.5px] font-medium text-teal">Compatibilité {Math.round(Number(match.overall_score))} %</p>
}

/** Détail du score de matching sur la page d'une offre. */
export function MatchPanel({ offerId }: { offerId: string }) {
  const { byOffer, loading } = useOfferMatches()
  const match = byOffer.get(offerId)
  if (loading) return null
  if (!match || match.overall_score === null) {
    return (
      <Panel title="Compatibilité avec votre profil">
        <p className="p-5 text-[13.5px] text-slate">Le score n’est pas encore calculé pour cette offre. Renseignez vos compétences dans votre profil.</p>
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
          {matched.length > 0 && <p><span className="font-medium text-navy">Compétences en commun : </span>{matched.join(', ')}</p>}
          {missing.length > 0 && <p><span className="font-medium text-navy">Compétences à acquérir : </span>{missing.join(', ')}</p>}
          <p className="text-[12px] text-slate">Calculé le {formatDate(match.calculated_at)}</p>
        </div>
      </div>
    </Panel>
  )
}
