import { Link } from 'react-router-dom'
import type { ReactNode } from 'react'
import type { MatchResult } from '../lib/matching'
import {
  APPLICATION_FLOW,
  STATUS_LABEL,
  flowIndex,
  statusTone,
} from '../lib/statusMachine'
import type { ApplicationStatus, ExtractedField, JobOffer, SkillImportance } from '../lib/types'
import { Badge } from './ui'
import { CONTRACT_LABEL, WORK_MODE_LABEL, cx, formatDate, formatPlace, formatSalary } from '../lib/format'

/* ------------------------------------------------------------------ */
/* Registre de correspondance                                          */
/*                                                                     */
/* Pièce maîtresse de l'interface : le score n'est pas affiché comme   */
/* un verdict, mais comme un calcul que l'on peut refaire à la main.   */
/* ------------------------------------------------------------------ */

const IMPORTANCE_LABEL: Record<SkillImportance, string> = {
  OBLIGATOIRE: 'Obligatoire',
  SOUHAITEE: 'Souhaitée',
}

export function MatchLedger({ match, compact = false }: { match: MatchResult; compact?: boolean }) {
  if (!match.available) {
    return (
      <div className="rounded-[10px] border border-dashed border-line bg-white px-5 py-6 text-center">
        <p className="text-sm font-medium text-navy">Score indisponible</p>
        <p className="mt-1 text-[13px] text-slate">
          Cette offre ne renseigne aucune compétence. La recherche par filtres reste possible.
        </p>
      </div>
    )
  }

  return (
    <div className="overflow-hidden rounded-[10px] border border-line bg-white">
      <div className="flex items-baseline justify-between border-b border-line bg-mist/50 px-5 py-3">
        <h3 className="text-[14px] font-semibold text-navy">Couverture des compétences demandées</h3>
        <span className="text-[12px] text-slate">poids 2 obligatoire · poids 1 souhaitée</span>
      </div>

      <ul className="divide-y divide-line/70">
        {match.lines.map((line) => (
          <li key={line.skillId} className="flex items-center gap-4 px-5 py-3">
            <CoverageMark state={line.state} />
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-medium text-navy">{line.skillName}</p>
              <p className="text-[12px] text-slate">
                {IMPORTANCE_LABEL[line.importance]} · poids {line.weight}
                {line.state === 'NON_VALIDEE' && ' · déclarée mais non confirmée'}
                {line.state === 'ABSENTE' && ' · absente du profil'}
              </p>
            </div>
            <span
              className={cx(
                'tnum w-14 shrink-0 text-right text-sm font-medium',
                line.earned > 0 ? 'text-navy' : 'text-slate/60',
              )}
            >
              {line.earned} / {line.weight}
            </span>
          </li>
        ))}
      </ul>

      <div className="flex items-baseline justify-between border-t-2 border-navy/15 px-5 py-3">
        <span className="text-[13px] font-medium text-navy">Points couverts</span>
        <span className="tnum text-sm font-semibold text-navy">
          {match.earnedPoints} sur {match.totalPoints}
        </span>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line bg-navy px-5 py-4">
        <code className="font-mono text-[15px] text-cyan">{match.formula}</code>
        <span className="text-[12px] text-white/55">{match.modelVersion}</span>
      </div>

      {!compact && (
        <p className="border-t border-line px-5 py-3 text-[12px] leading-relaxed text-slate">
          Le score mesure la couverture des compétences demandées. Ce n’est pas une probabilité d’embauche, et une
          compétence obligatoire manquante ne déclenche aucun refus automatique.
        </p>
      )}
    </div>
  )
}

function CoverageMark({ state }: { state: MatchResult['lines'][number]['state'] }) {
  if (state === 'COUVERTE') {
    return (
      <span aria-label="Compétence couverte" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-leaf/12 text-leaf">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    )
  }
  if (state === 'NON_VALIDEE') {
    return (
      <span aria-label="Compétence déclarée mais non confirmée" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-amber/15 text-[#946019]">
        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden>
          <path d="M8 4v5M8 11.5v.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
      </span>
    )
  }
  return (
    <span aria-label="Compétence absente du profil" className="flex h-6 w-6 shrink-0 items-center justify-center rounded-full bg-coral/10 text-coral">
      <svg width="12" height="12" viewBox="0 0 16 16" fill="none" aria-hidden>
        <path d="M4.5 4.5l7 7M11.5 4.5l-7 7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
      </svg>
    </span>
  )
}

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
/* Suivi de candidature                                                */
/* ------------------------------------------------------------------ */

export function StatusPill({ status }: { status: ApplicationStatus }) {
  const tone = statusTone(status)
  const map = { neutre: 'neutre', encours: 'encours', positif: 'positif', negatif: 'negatif' } as const
  return <Badge tone={map[tone]}>{STATUS_LABEL[status]}</Badge>
}

/** Frise du cycle nominal. Les sorties sont annoncées sous la frise. */
export function StatusTimeline({ status }: { status: ApplicationStatus }) {
  const current = flowIndex(status)
  const exited = current === -1

  return (
    <div>
      <ol className="flex items-center gap-0 overflow-x-auto pb-1">
        {APPLICATION_FLOW.map((step, index) => {
          const reached = !exited && index <= current
          const isCurrent = !exited && index === current
          return (
            <li key={step} className="flex min-w-0 shrink-0 items-center">
              <div className="flex flex-col items-center gap-1.5 px-1">
                <span
                  aria-hidden
                  className={cx(
                    'h-2.5 w-2.5 rounded-full border-2 transition-colors',
                    isCurrent
                      ? 'border-teal bg-teal ring-4 ring-teal/15'
                      : reached
                        ? 'border-teal bg-teal'
                        : 'border-line bg-white',
                  )}
                />
                <span className={cx('whitespace-nowrap text-[11px]', isCurrent ? 'font-semibold text-navy' : reached ? 'text-navy' : 'text-slate/70')}>
                  {STATUS_LABEL[step]}
                </span>
              </div>
              {index < APPLICATION_FLOW.length - 1 && (
                <span aria-hidden className={cx('mb-5 h-px w-8 sm:w-12', reached && index < current ? 'bg-teal' : 'bg-line')} />
              )}
            </li>
          )
        })}
      </ol>
      {exited && (
        <p className={cx('mt-2 text-[13px] font-medium', status === 'REJECTED' ? 'text-coral' : 'text-slate')}>
          Dossier {STATUS_LABEL[status].toLowerCase()} — le cycle s’arrête ici.
        </p>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Provenance des champs extraits du CV                                */
/* ------------------------------------------------------------------ */

export function ProvenanceRow({
  field,
  onConfirm,
  onCorrect,
}: {
  field: ExtractedField
  onConfirm: () => void
  onCorrect: (value: string) => void
}) {
  const settled = field.status !== 'PROPOSED'
  const lowConfidence = field.confidence < 0.6

  return (
    <li className={cx('px-5 py-4', settled && 'bg-mist/40')}>
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <p className="text-[12px] text-slate">{field.label}</p>
          <input
            defaultValue={field.correctedValue ?? field.value}
            onBlur={(e) => {
              if (e.target.value !== (field.correctedValue ?? field.value)) onCorrect(e.target.value)
            }}
            aria-label={field.label}
            className={cx(
              'mt-0.5 w-full rounded-[4px] border bg-transparent px-2 py-1 text-sm font-medium text-navy focus:border-teal focus:bg-white focus:outline-none',
              lowConfidence && !settled ? 'border-amber/60 bg-amber/5' : 'border-transparent hover:border-line',
            )}
          />
          <p className="mt-1.5 text-[12px] leading-relaxed text-slate">
            <span className="font-medium text-navy">Page {field.sourcePage}</span> · « {field.sourceExcerpt} »
          </p>
        </div>

        <div className="flex shrink-0 items-center gap-2">
          {lowConfidence && !settled && <Badge tone="attention">Lecture incertaine</Badge>}
          {field.status === 'CONFIRMED' && <Badge tone="positif">Confirmé</Badge>}
          {field.status === 'CORRECTED' && <Badge tone="teal">Corrigé</Badge>}
          {!settled && (
            <button onClick={onConfirm} className="rounded-[4px] border border-line px-2.5 py-1 text-[12px] font-medium text-navy hover:border-teal hover:text-teal">
              Confirmer
            </button>
          )}
        </div>
      </div>
    </li>
  )
}

/* ------------------------------------------------------------------ */
/* Carte d'offre                                                       */
/* ------------------------------------------------------------------ */

export function OfferCard({
  offer,
  organizationName,
  match,
  to,
  footer,
}: {
  offer: JobOffer
  organizationName: string
  match?: MatchResult
  to: string
  footer?: ReactNode
}) {
  return (
    <article className="rounded-[10px] border border-line bg-white p-4 shadow-panel transition-colors hover:border-teal/50">
      <div className="flex items-start gap-4">
        {match && <ScoreDial score={match.score} available={match.available} />}
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-center gap-2">
            <Link to={to} className="text-[15px] font-semibold text-navy hover:text-teal">
              {offer.title}
            </Link>
            <span className="text-[12px] text-slate">{offer.reference}</span>
          </div>
          <p className="mt-0.5 text-[13px] text-navy">{organizationName}</p>
          <p className="mt-1 text-[12px] text-slate">
            {formatPlace(offer.city, offer.governorate)} · {CONTRACT_LABEL[offer.contractType]} · {WORK_MODE_LABEL[offer.workMode]}
          </p>
          <p className="mt-1 text-[12px] text-slate">{formatSalary(offer.minSalary, offer.maxSalary)}</p>

          {match && match.available && match.missingSkillIds.length > 0 && (
            <p className="mt-2 text-[12px] text-coral">
              {match.missingSkillIds.length === 1 ? '1 compétence manquante' : `${match.missingSkillIds.length} compétences manquantes`}
              {match.mandatoryMissingCount > 0 && ` · dont ${match.mandatoryMissingCount} obligatoire${match.mandatoryMissingCount > 1 ? 's' : ''}`}
            </p>
          )}

          {!offer.easyApply && (
            <p className="mt-2 text-[12px] text-slate">Dépôt sur le site de l’employeur · suivi non disponible</p>
          )}

          {offer.applicationDeadline && (
            <p className="mt-1 text-[12px] text-slate">Clôture le {formatDate(offer.applicationDeadline)}</p>
          )}
        </div>
      </div>
      {footer && <div className="mt-3 border-t border-line pt-3">{footer}</div>}
    </article>
  )
}

/* ------------------------------------------------------------------ */
/* Mention de source                                                   */
/* ------------------------------------------------------------------ */

export function Citations({ items }: { items: Array<{ label: string; reference: string }> }) {
  if (items.length === 0) return null
  return (
    <p className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-[12px] text-slate">
      <span className="font-medium text-navy">Sources</span>
      {items.map((c) => (
        <span key={c.reference}>
          {c.label} <span className="text-slate/70">{c.reference}</span>
        </span>
      ))}
    </p>
  )
}
