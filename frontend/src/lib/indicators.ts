// Placement: frontend/src/lib/indicators.ts
import type { SkillGap } from '../api/reporting.ts'

/** The three skills whose offer demand most exceeds open training places; covered skills are left out. */
export function largestGaps(gaps: SkillGap[]): SkillGap[] {
  return gaps
    .filter((g) => g.offer_demand > g.training_supply)
    .sort((a, b) => (b.offer_demand - b.training_supply) - (a.offer_demand - a.training_supply))
    .slice(0, 3)
}
