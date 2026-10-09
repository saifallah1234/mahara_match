import { useState } from 'react'
import { PageBody, PageHeader } from './../components/layout'
import { Button, Cell, Panel, Row, Select, StatTile, Table } from './../components/ui'
import { BarChart, GapList } from './../components/charts'
import { useStore } from '../state/store'
import { REGIONAL_STATS, SKILL_DEMAND } from '../data/seed'

export function MinistereIndicateurs() {
  const [scope, setScope] = useState('national')

  const rows = scope === 'national' ? REGIONAL_STATS : REGIONAL_STATS.filter((r) => r.governorate === scope)
  const totals = rows.reduce(
    (acc, r) => ({
      offers: acc.offers + r.offers,
      applications: acc.applications + r.applications,
      hires: acc.hires + r.hires,
      trainings: acc.trainings + r.trainings,
    }),
    { offers: 0, applications: 0, hires: 0, trainings: 0 },
  )

  const conversion = totals.applications > 0 ? ((totals.hires / totals.applications) * 100).toFixed(1) : '0'

  return (
    <>
      <PageHeader
        title="Indicateurs de l’emploi"
        action={
          <>
            <Select value={scope} onChange={(e) => setScope(e.target.value)} className="min-w-48">
              <option value="national">Vue nationale</option>
              {REGIONAL_STATS.map((r) => (
                <option key={r.governorate} value={r.governorate}>
                  {r.governorate}
                </option>
              ))}
            </Select>
            <Button variant="secondaire">Exporter</Button>
          </>
        }
      />

      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={totals.offers.toLocaleString('fr-FR')} label="Offres ouvertes" />
          <StatTile value={totals.applications.toLocaleString('fr-FR')} label="Candidatures déposées" tone="teal" />
          <StatTile
            value={totals.hires.toLocaleString('fr-FR')}
            label="Recrutements déclarés"
            note={`${conversion} % des candidatures`}
            tone="leaf"
          />
          <StatTile value={totals.trainings.toLocaleString('fr-FR')} label="Formations suivies" />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <BarChart
            title="Offres ouvertes par gouvernorat"
            note="Données de démonstration, non représentatives du marché réel."
            data={REGIONAL_STATS.map((r) => ({ label: r.governorate, values: [r.offers] }))}
            series={['Offres ouvertes']}
            unit="offres"
          />

          <BarChart
            title="Recrutements déclarés par gouvernorat"
            note="Un recrutement est déclaré par l’employeur à la clôture du dossier."
            data={REGIONAL_STATS.map((r) => ({ label: r.governorate, values: [r.hires] }))}
            series={['Recrutements']}
            unit="recrutements"
          />
        </div>

        <Panel title="Détail par gouvernorat">
          <Table head={['Gouvernorat', 'Offres', 'Candidatures', 'Recrutements', 'Taux', 'Formations']}>
            {REGIONAL_STATS.map((region) => (
              <Row key={region.governorate}>
                <Cell className="font-medium text-navy">{region.governorate}</Cell>
                <Cell className="tnum text-slate">{region.offers.toLocaleString('fr-FR')}</Cell>
                <Cell className="tnum text-slate">{region.applications.toLocaleString('fr-FR')}</Cell>
                <Cell className="tnum text-slate">{region.hires.toLocaleString('fr-FR')}</Cell>
                <Cell className="tnum text-navy">{((region.hires / region.applications) * 100).toFixed(1)} %</Cell>
                <Cell className="tnum text-slate">{region.trainings.toLocaleString('fr-FR')}</Cell>
              </Row>
            ))}
          </Table>
        </Panel>

      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function MinistereCompetences() {
  const { skills } = useStore()

  const rows = SKILL_DEMAND.map((entry) => ({
    label: skills.find((s) => s.id === entry.skillId)?.canonicalName ?? entry.skillId,
    demand: entry.demand,
    supply: entry.trainingSeats,
  }))

  const tension = rows.filter((r) => r.demand > r.supply).length

  return (
    <>
      <PageHeader
        title="Compétences du marché"
        description="Comparaison entre les compétences demandées par les offres ouvertes et les places de formation disponibles."
      />

      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-3">
          <StatTile value={rows.length} label="Compétences suivies" />
          <StatTile value={tension} label="Compétences en tension" note="demande supérieure à l’offre de formation" tone="coral" />
          <StatTile
            value={rows.reduce((sum, r) => sum + r.supply, 0).toLocaleString('fr-FR')}
            label="Places de formation ouvertes"
            tone="leaf"
          />
        </div>

        <GapList
          title="Demande du marché face à l’offre de formation"
          note="Chaque compétence est reliée aux offres qui la réclament et aux formations qui l’enseignent."
          rows={rows}
        />

      </PageBody>
    </>
  )
}
