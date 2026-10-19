import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Cell, Panel, Row, Select, StatTile, Table } from '../../components/ui'
import { useIndicators } from '../../state/reporting'

export function Unavailable() {
  return (
    <Panel className="p-8">
      <p className="text-center text-[14px] text-slate">Les indicateurs ne sont pas encore disponibles : l’API de reporting n’est pas activée.</p>
    </Panel>
  )
}

export default function MinistereIndicateurs() {
  const { data, loading, error, unavailable } = useIndicators()
  const [scope, setScope] = useState('national')
  const regions = data?.regions ?? []
  const rows = scope === 'national' ? regions : regions.filter((r) => r.governorate === scope)
  const sum = (k: 'offers' | 'applications' | 'hires' | 'trainings') => rows.reduce((a, r) => a + r[k], 0)
  const conversion = sum('applications') > 0 ? ((sum('hires') / sum('applications')) * 100).toFixed(1) : '0'
  return (
    <>
      <PageHeader
        title="Indicateurs de l’emploi"
        action={
          <Select value={scope} onChange={(e) => setScope(e.target.value)} className="min-w-48">
            <option value="national">Vue nationale</option>
            {regions.map((r) => <option key={r.governorate} value={r.governorate}>{r.governorate}</option>)}
          </Select>
        }
      />
      <PageBody className="space-y-6">
        {error && <p role="alert" className="text-coral">{error}</p>}
        {loading ? <p className="text-slate">Chargement…</p> : unavailable ? <Unavailable /> : (
          <>
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              <StatTile value={sum('offers')} label="Offres" />
              <StatTile value={sum('applications')} label="Candidatures" tone="teal" />
              <StatTile value={sum('hires')} label="Recrutements" tone="leaf" note={`${conversion} % des candidatures`} />
              <StatTile value={sum('trainings')} label="Formations" tone="coral" />
            </div>
            <Panel title="Par gouvernorat">
              <Table head={['Gouvernorat', 'Offres', 'Candidatures', 'Recrutements', 'Formations']}>
                {rows.map((r) => (
                  <Row key={r.governorate}>
                    <Cell className="font-medium text-navy">{r.governorate}</Cell>
                    <Cell className="tnum">{r.offers}</Cell><Cell className="tnum">{r.applications}</Cell>
                    <Cell className="tnum">{r.hires}</Cell><Cell className="tnum">{r.trainings}</Cell>
                  </Row>
                ))}
              </Table>
            </Panel>
          </>
        )}
      </PageBody>
    </>
  )
}