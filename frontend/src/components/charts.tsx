import { useId, useState } from 'react'
import { cx, skillLabel } from '../lib/format'
import { largestGaps } from '../lib/indicators'
import type { SkillGap } from '../api/reporting'
import { Button, Table, Row, Cell } from './ui'

/**
 * Palette des graphiques.
 *
 * Teinte dérivée du teal de marque, remontée en saturation pour passer
 * le plancher de chroma ; l'ocre est le second rang. Le couple a été
 * vérifié sur les six contrôles (bande de clarté, chroma, séparation
 * sous déficience visuelle, lisibilité en vision normale, contraste).
 */
export const SERIES_COLORS = ['#0092A3', '#C77D1A'] as const

interface Datum {
  label: string
  values: number[]
}

function maxOf(data: Datum[]): number {
  return Math.max(1, ...data.flatMap((d) => d.values))
}

const formatValue = (n: number) => n.toLocaleString('fr-FR')

/* ------------------------------------------------------------------ */
/* Barres horizontales                                                 */
/* ------------------------------------------------------------------ */

export function BarChart({
  title,
  note,
  data,
  series,
  unit,
}: {
  title: string
  note?: string
  data: Datum[]
  /** un nom par série ; la légende n'apparaît qu'à partir de deux séries */
  series: string[]
  unit?: string
}) {
  const [asTable, setAsTable] = useState(false)
  const titleId = useId()
  const max = maxOf(data)
  const multi = series.length > 1

  return (
    <figure className="rounded-[10px] border border-line bg-white shadow-panel">
      <figcaption className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
        <div>
          <h3 id={titleId} className="text-[15px] font-semibold text-navy">
            {title}
          </h3>
          {note && <p className="mt-0.5 text-[12px] text-slate">{note}</p>}
        </div>
        <Button size="sm" variant="secondaire" onClick={() => setAsTable((v) => !v)}>
          {asTable ? 'Voir le graphique' : 'Voir le tableau'}
        </Button>
      </figcaption>

      {multi && !asTable && (
        <div className="flex flex-wrap gap-4 border-b border-line px-5 py-2.5">
          {series.map((name, i) => (
            <span key={name} className="flex items-center gap-2 text-[12px] text-navy">
              <span aria-hidden className="h-2.5 w-2.5 rounded-[2px]" style={{ background: SERIES_COLORS[i] }} />
              {name}
            </span>
          ))}
        </div>
      )}

      {asTable ? (
        <Table head={['', ...series.map((s) => (unit ? `${s} (${unit})` : s))]}>
          {data.map((d) => (
            <Row key={d.label}>
              <Cell className="font-medium">{d.label}</Cell>
              {d.values.map((v, i) => (
                <Cell key={i} className="tnum">
                  {formatValue(v)}
                </Cell>
              ))}
            </Row>
          ))}
        </Table>
      ) : (
        <ul aria-labelledby={titleId} className="space-y-3 px-5 py-4">
          {data.map((d) => (
            <li key={d.label}>
              <div className="mb-1 flex items-baseline justify-between gap-3">
                <span className="truncate text-[13px] text-navy">{d.label}</span>
                <span className="tnum shrink-0 text-[12px] font-medium text-slate">
                  {d.values.map(formatValue).join(' · ')}
                </span>
              </div>
              <div className={cx('flex flex-col', multi && 'gap-[2px]')}>
                {d.values.map((value, i) => (
                  <div
                    key={i}
                    title={`${d.label} — ${series[i]} : ${formatValue(value)}${unit ? ` ${unit}` : ''}`}
                    className="group relative h-2.5 cursor-default rounded-[2px] bg-mist/70"
                  >
                    <div
                      className="h-full rounded-r-[4px] transition-[width] duration-300"
                      style={{ width: `${(value / max) * 100}%`, background: SERIES_COLORS[i] }}
                    />
                  </div>
                ))}
              </div>
            </li>
          ))}
        </ul>
      )}
    </figure>
  )
}

/* ------------------------------------------------------------------ */
/* Écart entre deux mesures de même unité                              */
/* ------------------------------------------------------------------ */

export function GapList({
  title,
  note,
  rows,
}: {
  title: string
  note?: string
  rows: SkillGap[]
}) {
  const data = rows.map((r) => ({ label: skillLabel(r.skill), values: [r.offer_demand, r.training_supply] }))
  const top = largestGaps(rows)
  const topId = useId()
  return (
    <div className="space-y-3">
      {top.length > 0 && (
        <section aria-labelledby={topId} className="rounded-[10px] border border-coral/30 bg-white px-5 py-4 shadow-panel">
          <h3 id={topId} className="text-[15px] font-semibold text-navy">Les trois plus grands écarts</h3>
          <ol className="mt-2 space-y-1.5">
            {top.map((r) => (
              <li key={r.skill} className="flex items-baseline gap-2 text-[13px] text-navy">
                <span aria-hidden className="mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
                <span>
                  <span className="font-medium">{skillLabel(r.skill)}</span> : {formatValue(r.offer_demand)} offres pour{' '}
                  {formatValue(r.training_supply)} places de formation.
                </span>
              </li>
            ))}
          </ol>
        </section>
      )}
      <BarChart
        title={title}
        note={note}
        data={data}
        series={['Offres demandant la compétence', 'Places de formation ouvertes']}
      />
    </div>
  )
}
