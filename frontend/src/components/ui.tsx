import { Children, cloneElement, createContext, isValidElement, useContext, useEffect, useRef, useState, type ReactElement, type ButtonHTMLAttributes, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from 'react'
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

/** Placeholder bars shown while a list loads; the hidden text keeps « Chargement… » for screen readers. */
export function Loading() {
  return (
    <div role="status" className="space-y-3 px-5 py-4">
      <span className="sr-only">Chargement…</span>
      {[0, 1, 2].map((i) => (
        <div key={i} aria-hidden className="space-y-1.5">
          <div className="h-3.5 w-2/5 animate-pulse rounded bg-mist" />
          <div className="h-3 w-3/4 animate-pulse rounded bg-mist/70" />
        </div>
      ))}
    </div>
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
  'w-full rounded-[6px] border border-line bg-white px-3 py-2 text-sm text-navy placeholder:text-slate focus:border-teal'

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

// Column titles, so each cell can label itself when the table becomes stacked cards on phones.
const TableHead = createContext<ReactNode[]>([])

export function Table({ head, children }: { head: ReactNode[]; children: ReactNode }) {
  return (
    <div className="sm:overflow-x-auto">
      <table className="block w-full border-collapse text-sm sm:table">
        <thead className="hidden sm:table-header-group">
          <tr className="border-b border-line text-left">
            {head.map((cell, i) => (
              <th key={i} className="px-5 py-2.5 text-[12px] font-semibold text-slate">
                {cell}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="block sm:table-row-group">
          <TableHead.Provider value={head}>{children}</TableHead.Provider>
        </tbody>
      </table>
    </div>
  )
}

export function Row({ children, onClick }: { children: ReactNode; onClick?: () => void }) {
  const head = useContext(TableHead)
  let column = 0
  const cells = Children.map(children, (child) =>
    isValidElement(child) && child.type === Cell ? cloneElement(child as ReactElement<CellProps>, { label: head[column++] }) : child,
  )
  return (
    <tr
      onClick={onClick}
      className={cx('block border-b border-line/70 py-2 last:border-0 sm:table-row sm:py-0', onClick && 'cursor-pointer hover:bg-mist/60')}
    >
      {cells}
    </tr>
  )
}

type CellProps = { children: ReactNode; className?: string; label?: ReactNode }

export function Cell({ children, className, label }: CellProps) {
  return (
    <td className={cx('block px-5 py-1 align-middle sm:table-cell sm:py-3', className)}>
      {label && <span className="block text-left text-[11px] font-semibold text-slate sm:hidden">{label}</span>}
      {children}
    </td>
  )
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
  const dialogRef = useRef<HTMLDivElement>(null)
  const onCloseRef = useRef(onClose)

  useEffect(() => { onCloseRef.current = onClose })

  useEffect(() => {
    if (!open) return
    dialogRef.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') onCloseRef.current() }
    document.addEventListener('keydown', onKey)
    return () => document.removeEventListener('keydown', onKey)
  }, [open])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-navy/35 p-0 sm:items-center sm:p-6" onClick={onClose}>
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        tabIndex={-1}
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

/** Confirmation d'une action terminale ou destructive. Monté seulement quand il est ouvert, donc son champ repart vide. */
export function ConfirmDialog({
  title,
  children,
  reasonLabel,
  danger = false,
  onConfirm,
  onCancel,
}: {
  title: string
  children: ReactNode
  reasonLabel?: string
  danger?: boolean
  onConfirm: (reason: string) => void
  onCancel: () => void
}) {
  const [reason, setReason] = useState('')
  return (
    <Modal
      open
      onClose={onCancel}
      title={title}
      footer={
        <>
          <Button variant="secondaire" onClick={onCancel}>Annuler</Button>
          <Button variant={danger ? 'danger' : 'primaire'} onClick={() => onConfirm(reason.trim())}>Confirmer</Button>
        </>
      }
    >
      <div className="space-y-4 text-[13.5px] leading-relaxed text-slate">
        {children}
        {reasonLabel && (
          <Field label={reasonLabel}>
            <Textarea value={reason} onChange={(e) => setReason(e.target.value)} />
          </Field>
        )}
      </div>
    </Modal>
  )
}
