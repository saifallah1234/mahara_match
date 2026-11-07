import type { Offer } from '../api/candidate'
import type { OfferMatch } from '../api/matching'

export function filterCandidateOffers(offers: Offer[], contract: string, mode: string): Offer[] {
  return offers.filter((offer) =>
    (!contract || offer.contract_type === contract) &&
    (!mode || (mode === 'platform' ? offer.easy_apply : !offer.easy_apply)),
  )
}

type ScoredMatch = Pick<OfferMatch, 'overall_score' | 'explanation_json'>

/** What an offer card shows for a match: rounded score and up to two missing skills; null without a score. */
export function matchBadge(match: ScoredMatch | undefined): { score: number; missing: string[] } | null {
  if (!match || match.overall_score === null) return null
  return { score: Math.round(Number(match.overall_score)), missing: (match.explanation_json?.missing_skills ?? []).slice(0, 2) }
}

/** The calculate action runs by itself once per session, when skills exist and scores are missing or stale. */
export function shouldAutoCalculate(state: { hasSkills: boolean; hasMatches: boolean; stale: boolean; alreadyTried: boolean }): boolean {
  return state.hasSkills && !state.alreadyTried && (!state.hasMatches || state.stale)
}
