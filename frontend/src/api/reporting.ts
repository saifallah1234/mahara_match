import { ApiError, request } from './client.ts'

/** CONTRAT PROPOSÉ pour l'équipe backend : GET /reporting/indicators/ */
export type RegionIndicator = { governorate: string; offers: number; applications: number; hires: number; trainings: number }
export type SkillGap = { skill: string; offer_demand: number; training_supply: number }
export type Indicators = { regions: RegionIndicator[]; skill_gaps: SkillGap[] }

export async function getIndicators(): Promise<Indicators | null> {
  try { return await request<Indicators>('/reporting/indicators/') }
  catch (e) { if (e instanceof ApiError && e.status === 404) return null; throw e }
}