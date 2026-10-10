import { allPages } from './auth.ts'

export type OfferMatch = {
  id: string; offer_id: string; model_version: string
  overall_score: string | null; skill_score: string | null
  experience_score: string | null; location_score: string | null
  explanation_json: { matched_skills?: string[]; missing_skills?: string[] } | null
  calculated_at: string
}
export type CvAnalysis = {
  id: string; cv: string; target_offer: string | null; overall_score: string | null
  issues_json: unknown; suggestions_json: unknown; analyzed_at: string
}

export const listOfferMatches = () => allPages<OfferMatch>('/offer-matches/')
export const listCvAnalyses = () => allPages<CvAnalysis>('/cv-analysis-results/')