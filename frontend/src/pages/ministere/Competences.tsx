import { PageBody, PageHeader } from '../../components/layout'
import { GapList } from '../../components/charts'
import { Loading, Panel } from '../../components/ui'
import { useIndicators } from '../../state/reporting'
import { DEMO_CAPTION, Unavailable } from './Indicateurs'

export default function MinistereCompetences() {
  const { data, loading, error, unavailable } = useIndicators()
  return (
    <>
      <PageHeader title="Compétences : demande et formation" />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {loading ? <Panel><Loading /></Panel> : unavailable ? <Unavailable /> : (
          <>
            <p className="text-[13px] text-slate">{DEMO_CAPTION}</p>
            <GapList title="Écart entre les offres et les formations" rows={data?.skill_gaps ?? []} />
          </>
        )}
      </PageBody>
    </>
  )
}
