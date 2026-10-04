import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, SelectHTMLAttributes, TextareaHTMLAttributes } from 'react'
import { cx } from '../lib/format'

/* ------------------------------------------------------------------ */
/* Boutons                                                             */
/* ------------------------------------------------------------------ */

type ButtonVariant = 'primaire' | 'secondaire' | 'discret' | 'danger'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: ButtonVariant
  size?: 'sm' | 'md'
}

const BUTTON_STYLES: Record<ButtonVariant, string> = {
  primaire: 'bg-teal text-white hover:bg-teal-deep disabled:bg-slate/40',
  secondaire: 'bg-white text-navy border border-line hover:border-teal hover:text-teal disabled:text-slate/50',
  discret: 'bg-transparent text-slate hover:text-navy hover:bg-mist',
  danger: 'bg-white text-coral border border-coral/40 hover:bg-coral hover:text-white',
}

export function Button({ variant = 'primaire', size = 'md', className, ...rest }: ButtonProps) {
  return (
    <button
      {...rest}
      className={cx(
        'inline-flex items-center justify-center gap-2 rounded-[6px] font-medium transition-colors disabled:cursor-not-allowed',
        size === 'sm' ? 'px-3 py-1.5 text-[13px]' : 'px-4 py-2 text-sm',
        BUTTON_STYLES[variant],
        className,
      )}
    />
  )
}

/* ------------------------------------------------------------------ */
/* Surfaces                                                            */
/* ------------------------------------------------------------------ */

export function Panel({
  children,
  className,
  title,
  description,
  action,
}: {
  children: ReactNode
  className?: string
  title?: ReactNode
  description?: ReactNode
  action?: ReactNode
}) {
  return (
    <section className={cx('rounded-[10px] border border-line bg-white shadow-panel', className)}>
      {(title || action) && (
        <header className="flex flex-wrap items-start justify-between gap-3 border-b border-line px-5 py-4">
          <div className="min-w-0">
            {title && <h2 className="text-[15px] font-semibold text-navy">{title}</h2>}
            {description && <p className="mt-0.5 text-[13px] text-slate">{description}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  )
}

export function EmptyState({ title, children, action }: { title: string; children?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex flex-col items-center gap-3 px-6 py-14 text-center">
      <div aria-hidden className="h-9 w-9 rounded-full border-2 border-dashed border-line" />
      <p className="text-sm font-medium text-navy">{title}</p>
      {children && <p className="max-w-sm text-[13px] text-slate">{children}</p>}
      {action}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Étiquettes                                                          */
/* ------------------------------------------------------------------ */

type BadgeTone = 'neutre' | 'teal' | 'positif' | 'negatif' | 'attention' | 'encours'

const BADGE_STYLES: Record<BadgeTone, string> = {
  neutre: 'bg-mist text-slate',
  teal: 'bg-cyan-soft text-teal-dark',
  positif: 'bg-leaf/12 text-leaf',
  negatif: 'bg-coral/10 text-coral',
  attention: 'bg-amber/15 text-[#946019]',
  encours: 'bg-teal/10 text-teal-deep',
}

export function Badge({ tone = 'neutre', children }: { tone?: BadgeTone; children: ReactNode }) {
  return (
    <span className={cx('inline-flex items-center gap-1 rounded-[4px] px-2 py-0.5 text-[12px] font-medium', BADGE_STYLES[tone])}>
      {children}
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* Formulaires                                                         */
/* ------------------------------------------------------------------ */

export function Field({
  label,
  hint,
  required,
  children,
}: {
  label: string
  hint?: ReactNode
  required?: boolean
  children: ReactNode
}) {
  return (
    <label className="block">
      <span className="mb-1 block text-[13px] font-medium text-navy">
        {label}
        {required && <span className="ml-1 text-coral">*</span>}
      </span>
      {children}
      {hint && <span className="mt-1 block text-[12px] text-slate">{hint}</span>}
    </label>
  )
}

const CONTROL =
  'w-full rounded-[6px] border border-line bg-white px-3 py-2 text-sm text-navy placeholder:text-slate/60 focus:border-teal focus:outline-none'

export function Input({ className, ...rest }: InputHTMLAttributes<HTMLInputElement>) {
  return <input {...rest} className={cx(CONTROL, className)} />
}

export function Textarea({ className, ...rest }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea {...rest} className={cx(CONTROL, 'min-h-24 resize-y leading-relaxed', className)} />
}

export function Select({ className, children, ...rest }: SelectHTMLAttributes<HTMLSelectElement>) {
  return (
    <select {...rest} className={cx(CONTROL, 'appearance-none bg-white pr-8', className)}>
      {children}
    </select>
  )
}

/* ------------------------------------------------------------------ */
/* Tableaux                                                            */
/* ------------------------------------------------------------------ */

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="overflow-x-auto">
      <table className="w-full border-collapse text-sm">
        <thead>
          <tr className="border-b border-line text-left">
            {head.map((cell, i) => (
              <th key={i} className="px-5 py-2.5 text-[12px] font-semibold text-slate">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>{children}</tbody>
      </table>
    </div>
  )
}

export function Row({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  return (
    <tr
      onClick={onClick}
      className={cx('border-b border-line/70 last:border-0', onClick && 'cursor-pointer hover:bg-mist/60')}
    >
      {children}
    </tr>
  )
}

export function Cell({ children, className }: { children: ReactNode; className?: string }) {
  return <td className={cx('px-5 py-3 align-middle', className)}>{children}</td>
}

/* ------------------------------------------------------------------ */
/* Indicateurs                                                         */
/* ------------------------------------------------------------------ */

export function Meter({ value, label, tone = 'teal' }: { value: number; label?: string; tone?: 'teal' | 'amber' | 'leaf' }) {
  const color = tone === 'teal' ? 'bg-teal' : tone === 'amber' ? 'bg-amber' : 'bg-leaf'
  return (
    <div>
      {label && (
        <div className="mb-1 flex items-baseline justify-between text-[12px]">
          <span className="text-slate">{label}</span>
          <span className="tnum font-medium text-navy">{value} %</span>
        </div>
      )}
      <div className="h-1.5 overflow-hidden rounded-full bg-mist">
        <div className={cx('h-full rounded-full', color)} style={{ width: `${Math.min(100, Math.max(0, value))}%` }} />
      </div>
    </div>
  )
}

export function StatTile({
  value,
  label,
  note,
  tone = 'navy',
}: {
  value: ReactNode
  label: string
  note?: string
  tone?: 'navy' | 'teal' | 'coral' | 'leaf'
}) {
  const valueColor =
    tone === 'teal' ? 'text-teal' : tone === 'coral' ? 'text-coral' : tone === 'leaf' ? 'text-leaf' : 'text-navy'
  return (
    <div className="rounded-[10px] border border-line bg-white px-4 py-3.5 shadow-panel">
      <p className={cx('tnum text-2xl font-semibold leading-none', valueColor)}>{value}</p>
      <p className="mt-1.5 text-[13px] text-navy">{label}</p>
      {note && <p className="mt-0.5 text-[12px] text-slate">{note}</p>}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Avertissements                                                      */
/* ------------------------------------------------------------------ */

export function Note({ tone = 'info', children }: { tone?: 'info' | 'attention' | 'danger'; children: ReactNode }) {
  const styles = {
    info: 'border-l-teal bg-mist/70 text-navy',
    attention: 'border-l-amber bg-amber/8 text-navy',
    danger: 'border-l-coral bg-coral/6 text-navy',
  }[tone]
  return <div className={cx('rounded-r-[6px] border-l-[3px] px-4 py-3 text-[13px] leading-relaxed', styles)}>{children}</div>
}

/* ------------------------------------------------------------------ */
/* Onglets                                                             */
/* ------------------------------------------------------------------ */

export function Tabs<T extends string>({
  tabs,
  active,
  onChange,
}: {
  tabs: Array<{ id: T; label: string; count?: number }>
  active: T
  onChange: (id: T) => void
}) {
  return (
    <div role="tablist" className="flex flex-wrap gap-1 border-b border-line">
      {tabs.map((tab) => {
        const selected = tab.id === active
        return (
          <button
            key={tab.id}
            role="tab"
            aria-selected={selected}
            onClick={() => onChange(tab.id)}
            className={cx(
              '-mb-px border-b-2 px-3.5 py-2 text-[13px] font-medium transition-colors',
              selected ? 'border-teal text-teal' : 'border-transparent text-slate hover:text-navy',
            )}
          >
            {tab.label}
            {tab.count != null && <span className="tnum ml-1.5 text-slate">{tab.count}</span>}
          </button>
        )
      })}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Fenêtre modale                                                      */
/* ------------------------------------------------------------------ */

export function Modal({
  open,
  onClose,
  title,
  children,
  footer,
}: {
  open: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
}) {
  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy/35 p-0 sm:items-center sm:p-6" onClick={onClose}>
      <div
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
        className="max-h-[88vh] w-full max-w-lg overflow-y-auto rounded-t-[12px] bg-white shadow-lift sm:rounded-[12px]"
      >
        <header className="flex items-center justify-between border-b border-line px-5 py-3.5">
          <h2 className="text-[15px] font-semibold text-navy">{title}</h2>
          <button onClick={onClose} aria-label="Fermer" className="rounded p-1 text-slate hover:bg-mist hover:text-navy">
            <svg width="16" height="16" viewBox="0 0 16 16" fill="none" aria-hidden>
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </header>
        <div className="px-5 py-4">{children}</div>
        {footer && <footer className="flex justify-end gap-2 border-t border-line px-5 py-3.5">{footer}</footer>}
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* Notifications éphémères                                             */
/* ------------------------------------------------------------------ */

export function ToastStack({
  toasts,
  onDismiss,
}: {
  toasts: Array<{ id: number; tone: 'succes' | 'echec' | 'info'; message: string }>
  onDismiss: (id: number) => void
}) {
  if (toasts.length === 0) return null
  return (
    <div className="fixed bottom-4 left-1/2 z-50 flex w-[min(28rem,calc(100vw-2rem))] -translate-x-1/2 flex-col gap-2">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          role="status"
          className={cx(
            'flex items-start gap-3 rounded-[8px] border px-4 py-3 text-[13px] shadow-lift',
            toast.tone === 'succes' && 'border-leaf/30 bg-white text-navy',
            toast.tone === 'echec' && 'border-coral/40 bg-white text-navy',
            toast.tone === 'info' && 'border-line bg-white text-navy',
          )}
        >
          <span
            aria-hidden
            className={cx(
              'mt-1.5 h-1.5 w-1.5 shrink-0 rounded-full',
              toast.tone === 'succes' && 'bg-leaf',
              toast.tone === 'echec' && 'bg-coral',
              toast.tone === 'info' && 'bg-teal',
            )}
          />
          <p className="flex-1 leading-snug">{toast.message}</p>
          <button onClick={() => onDismiss(toast.id)} aria-label="Fermer" className="text-slate hover:text-navy">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" aria-hidden>
              <path d="M4 4l8 8M12 4l-8 8" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
            </svg>
          </button>
        </div>
      ))}
    </div>
  )
}
