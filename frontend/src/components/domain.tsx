import { Link } from 'react-router-dom'
import { citationPath } from '../lib/citations'
import type { RoleCode } from '../lib/types'

/* ------------------------------------------------------------------ */
/* Pastille de score                                                   */
/* ------------------------------------------------------------------ */

/** Pastille de score compacte, pour les listes. */
export function ScoreDial({ score, available, size = 56 }: { score: number; available: boolean; size?: number }) {
  if (!available) {
    return (
      <div
        style={{ width: size, height: size }}
        className="flex shrink-0 flex-col items-center justify-center rounded-full border border-dashed border-line text-[10px] leading-tight text-slate"
      >
        score
        <br />
        n. d.
      </div>
    )
  }

  const radius = size / 2 - 4
  const circumference = 2 * Math.PI * radius
  const filled = (score / 100) * circumference
  const stroke = score >= 70 ? 'var(--color-teal)' : score >= 40 ? 'var(--color-amber)' : 'var(--color-coral)'

  return (
    <div style={{ width: size, height: size }} className="relative shrink-0">
      <svg width={size} height={size} className="-rotate-90" aria-hidden>
        <circle cx={size / 2} cy={size / 2} r={radius} fill="none" stroke="var(--color-mist)" strokeWidth="4" />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={stroke}
          strokeWidth="4"
          strokeLinecap="round"
          strokeDasharray={`${filled} ${circumference}`}
        />
      </svg>
      <span
        className="tnum absolute inset-0 flex items-baseline justify-center font-semibold leading-none text-navy"
        style={{ fontSize: size * (score === 100 ? 0.2 : 0.24), paddingTop: size * 0.4 }}
      >
        {score}
        <span style={{ fontSize: size * 0.15 }}>%</span>
      </span>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Mention de source                                                   */
/* ------------------------------------------------------------------ */

export function Citations({ items, role }: { items: Array<{ label: string; reference: string }>; role: RoleCode }) {
  if (items.length === 0) return null
  return (
    <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-slate">
      <span className="font-medium text-navy">Sources</span>
      {items.map((c) => {
        const to = citationPath(c.reference, role)
        return (
          <span key={c.reference}>
            {to ? <Link to={to} className="text-teal hover:underline">{c.label}</Link> : c.label}{' '}
            <span className="text-slate/70">{c.reference}</span>
          </span>
        )
      })}
    </p>
  )
}
