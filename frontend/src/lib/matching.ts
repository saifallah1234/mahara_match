/**
 * Moteur de correspondance candidat / offre.
 *
 * Règle appliquée (Fiche 3) : poids 2 pour une compétence obligatoire,
 * poids 1 pour une compétence souhaitée. Le score est le rapport des
 * points couverts sur les points demandés, exprimé en pourcentage.
 *
 *     score = 100 × points couverts / points demandés
 *
 * Le score mesure une couverture de compétences. Ce n'est ni une
 * probabilité d'embauche, ni un motif de refus automatique.
 */

import {
  SKILL_WEIGHT,
  type CandidateProfile,
  type JobOffer,
  type Skill,
  type SkillImportance,
  type SkillLevel,
  type UUID,
} from './types'

export const MATCH_MODEL_VERSION = 'couverture-ponderee-v1'

export type CoverageState =
  /** le candidat a confirmé cette compétence */
  | 'COUVERTE'
  /** le candidat a déclaré la compétence sans l'avoir validée */
  | 'NON_VALIDEE'
  /** la compétence n'apparaît pas dans le profil */
  | 'ABSENTE'

export interface SkillLine {
  skillId: UUID
  skillName: string
  importance: SkillImportance
  requiredLevel: SkillLevel
  weight: number
  state: CoverageState
  candidateLevel?: SkillLevel
  /** points obtenus sur cette ligne */
  earned: number
}

export interface MatchResult {
  /** false quand l'offre ne renseigne aucune compétence */
  available: boolean
  modelVersion: string
  lines: SkillLine[]
  earnedPoints: number
  totalPoints: number
  /** arrondi à l'entier, comme affiché à l'utilisateur */
  score: number
  /** l'expression littérale du calcul, pour pouvoir le refaire à la main */
  formula: string
  missingSkillIds: UUID[]
  mandatoryMissingCount: number
  /** indicateurs de contexte, volontairement hors du score */
  sameGovernorate: boolean
  workModeCompatible: boolean
}

/** Une compétence n'est comptée que si le candidat l'a confirmée. */
function coverageOf(profile: CandidateProfile, skillId: UUID): { state: CoverageState; level?: SkillLevel } {
  const owned = profile.skills.find((s) => s.skillId === skillId)
  if (!owned) return { state: 'ABSENTE' }
  if (!owned.validated) return { state: 'NON_VALIDEE', level: owned.level }
  return { state: 'COUVERTE', level: owned.level }
}

export function computeMatch(
  profile: CandidateProfile,
  offer: JobOffer,
  skills: Skill[],
): MatchResult {
  const nameOf = (id: UUID) => skills.find((s) => s.id === id)?.canonicalName ?? id

  const lines: SkillLine[] = offer.skills.map((os) => {
    const weight = SKILL_WEIGHT[os.importance]
    const { state, level } = coverageOf(profile, os.skillId)
    return {
      skillId: os.skillId,
      skillName: nameOf(os.skillId),
      importance: os.importance,
      requiredLevel: os.requiredLevel,
      weight,
      state,
      candidateLevel: level,
      earned: state === 'COUVERTE' ? weight : 0,
    }
  })

  const totalPoints = lines.reduce((sum, l) => sum + l.weight, 0)
  const earnedPoints = lines.reduce((sum, l) => sum + l.earned, 0)
  const available = totalPoints > 0

  const missing = lines.filter((l) => l.state !== 'COUVERTE')

  return {
    available,
    modelVersion: MATCH_MODEL_VERSION,
    lines,
    earnedPoints,
    totalPoints,
    score: available ? Math.round((100 * earnedPoints) / totalPoints) : 0,
    formula: available ? `100 × ${earnedPoints} / ${totalPoints} = ${Math.round((100 * earnedPoints) / totalPoints)} %` : 'score indisponible',
    missingSkillIds: missing.map((l) => l.skillId),
    mandatoryMissingCount: missing.filter((l) => l.importance === 'OBLIGATOIRE').length,
    sameGovernorate: profile.governorate === offer.governorate,
    workModeCompatible:
      offer.workMode === 'REMOTE' ||
      profile.preferredWorkMode === offer.workMode ||
      profile.relocation === 'OPEN_TO_RELOCATE',
  }
}

/**
 * Classe les offres ouvertes par couverture décroissante.
 *
 * À score égal, l'offre qui demande le plus de points passe devant : une
 * offre ne réclamant qu'une compétence souhaitée atteint 100 % sans rien
 * dire du poste, et ne doit pas éclipser une offre exigeante couverte à
 * 80 %. Le score affiché reste celui du calcul documenté ; seul l'ordre
 * de présentation tient compte de l'exigence de l'offre.
 */
export function rankOffers(
  profile: CandidateProfile,
  offers: JobOffer[],
  skills: Skill[],
): Array<{ offer: JobOffer; match: MatchResult }> {
  return offers
    .filter((o) => o.status === 'PUBLISHED')
    .map((offer) => ({ offer, match: computeMatch(profile, offer, skills) }))
    .sort((a, b) => {
      if (a.match.available !== b.match.available) return a.match.available ? -1 : 1
      if (b.match.score !== a.match.score) return b.match.score - a.match.score
      return b.match.totalPoints - a.match.totalPoints
    })
}

/** Nombre de points en dessous duquel une offre ne qualifie pas vraiment le poste. */
export const SUBSTANTIAL_POINTS = 3

/**
 * Meilleure correspondance à mettre en avant : la première offre dont les
 * exigences sont assez étoffées pour que le score veuille dire quelque chose.
 */
export function headlineMatch(
  ranked: Array<{ offer: JobOffer; match: MatchResult }>,
): { offer: JobOffer; match: MatchResult } | undefined {
  return ranked.find((r) => r.match.available && r.match.totalPoints >= SUBSTANTIAL_POINTS) ?? ranked[0]
}

/**
 * Écarts de compétences du candidat, tous postes confondus.
 * Sert à proposer des formations reliées à une compétence manquante
 * identifiable — jamais une recommandation sans raison.
 */
export function skillGaps(
  profile: CandidateProfile,
  offers: JobOffer[],
  skills: Skill[],
): Array<{ skillId: UUID; skillName: string; demandCount: number; mandatoryCount: number }> {
  const tally = new Map<UUID, { demandCount: number; mandatoryCount: number }>()

  for (const offer of offers.filter((o) => o.status === 'PUBLISHED')) {
    const match = computeMatch(profile, offer, skills)
    for (const line of match.lines) {
      if (line.state === 'COUVERTE') continue
      const current = tally.get(line.skillId) ?? { demandCount: 0, mandatoryCount: 0 }
      current.demandCount += 1
      if (line.importance === 'OBLIGATOIRE') current.mandatoryCount += 1
      tally.set(line.skillId, current)
    }
  }

  return [...tally.entries()]
    .map(([skillId, counts]) => ({
      skillId,
      skillName: skills.find((s) => s.id === skillId)?.canonicalName ?? skillId,
      ...counts,
    }))
    .sort((a, b) => b.demandCount - a.demandCount)
}

/** Correspondance inverse : classe les candidats pour une offre donnée. */
export function rankCandidates(
  profiles: CandidateProfile[],
  offer: JobOffer,
  skills: Skill[],
): Array<{ profile: CandidateProfile; match: MatchResult }> {
  return profiles
    .map((profile) => ({ profile, match: computeMatch(profile, offer, skills) }))
    .sort((a, b) => b.match.score - a.match.score)
}
