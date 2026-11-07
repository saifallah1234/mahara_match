import { PageBody, PageHeader } from '../../components/layout'
import { Panel } from '../../components/ui'
import { useIndicators } from '../../state/reporting'
import { Unavailable } from './Indicateurs'
import { skillLabel } from '../../lib/format'

export default function MinistereCompetences() {
  const { data, loading, error, unavailable } = useIndicators()
  const gaps = [...(data?.skill_gaps ?? [])].sort((a, b) => (b.offer_demand - b.training_supply) - (a.offer_demand - a.training_supply))
  const max = Math.max(1, ...gaps.map((g) => Math.max(g.offer_demand, g.training_supply)))
  return (
    <>
      <PageHeader title="Compétences : demande et formation" />
      <PageBody>
        {error && <p role="alert" className="mb-3 text-coral">{error}</p>}
        {loading ? <p className="text-slate">Chargement…</p> : unavailable ? <Unavailable /> : (
          <Panel title="Écart entre les offres et les formations">
            <ul className="space-y-4 p-5">
              {gaps.map((g) => (
                <li key={g.skill} className="text-[13.5px]">
                  <p className="font-medium text-navy">{skillLabel(g.skill)}</p>
                  <div className="mt-1 space-y-1">
                    <div className="flex items-center gap-2"><span className="w-20 text-[12px] text-slate">Offres</span><div className="h-2 rounded bg-teal" style={{ width: `${(g.offer_demand / max) * 100}%` }} /><span className="tnum text-[12px]">{g.offer_demand}</span></div>
                    <div className="flex items-center gap-2"><span className="w-20 text-[12px] text-slate">Formations</span><div className="h-2 rounded bg-leaf" style={{ width: `${(g.training_supply / max) * 100}%` }} /><span className="tnum text-[12px]">{g.training_supply}</span></div>
                  </div>
                </li>
              ))}
            </ul>
          </Panel>
        )}
      </PageBody>
    </>
  )
}