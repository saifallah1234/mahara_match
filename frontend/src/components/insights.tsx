import { EmptyState, Panel } from './ui'
import { ScoreDial } from './domain'
import { useCandidate } from '../state/candidate'
import { useCvAnalyses, useOfferMatches } from '../state/insights'
import { formatDate } from '../lib/format'

const text = (item: unknown): string => {
  if (typeof item === 'string') return item
  if (item && typeof item === 'object') {
    const o = item as Record<string, unknown>
    for (const key of ['message', 'text', 'title', 'description']) if (typeof o[key] === 'string') return o[key] as string
  }
  return JSON.stringify(item)
}
const asList = (value: unknown): unknown[] => (Array.isArray(value) ? value : [])

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

/** Résultats d'analyse ATS, affichés sur la page « Mes CV ». */
export function AtsPanel() {
  const { analyses, loading } = useCvAnalyses()
  const { cvs } = useCandidate()
  return (
    <Panel title="Analyse ATS de mon CV">
      {loading ? <p className="p-5 text-slate">Chargement…</p> : analyses.length === 0 ? (
        <EmptyState title="Aucune analyse pour le moment">
          Les scores et suggestions d’amélioration de votre CV apparaîtront ici.
        </EmptyState>
      ) : (
        <ul className="divide-y divide-line/70">
          {analyses.slice(0, 3).map((a) => {
            const cv = cvs.find((c) => c.id === a.cv)
            const issues = asList(a.issues_json)
            const tips = asList(a.suggestions_json)
            return (
              <li key={a.id} className="flex flex-wrap items-start gap-5 px-5 py-4">
                <ScoreDial score={Math.round(Number(a.overall_score ?? 0))} available={a.overall_score !== null} size={64} />
                <div className="min-w-0 flex-1 space-y-2 text-[13.5px]">
                  <p className="font-medium text-navy">{cv ? `v${cv.version_number} — ${cv.title}` : 'CV'} · {formatDate(a.analyzed_at)}</p>
                  {issues.length > 0 && (
                    <div><p className="text-slate">Points à corriger</p><ul className="list-disc pl-5">{issues.map((i, n) => <li key={n}>{text(i)}</li>)}</ul></div>
                  )}
                  {tips.length > 0 && (
                    <div><p className="text-slate">Suggestions</p><ul className="list-disc pl-5">{tips.map((t, n) => <li key={n}>{text(t)}</li>)}</ul></div>
                  )}
                </div>
              </li>
            )
          })}
        </ul>
      )}
    </Panel>
  )
}