// Placement: frontend/src/components/notifications.tsx
import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { listNotifications, markNotificationRead, type AppNotification } from '../api/notifications'
import { cx, formatDateTime } from '../lib/format'
import { notificationPath } from '../lib/notifications'
import type { RoleCode } from '../lib/types'
import { Button } from './ui'

const POLL_MS = 60_000

/** Bell with unread count. Polls every minute while the tab is visible. */
export function NotificationBell({ role }: { role: RoleCode }) {
  const navigate = useNavigate()
  const [items, setItems] = useState<AppNotification[]>([])
  const [open, setOpen] = useState(false)
  const [error, setError] = useState<string | null>(null)
  // shortcut: the badge counts unread items among the newest 20, add an unread filter to the API when volume grows.
  const unread = items.filter((item) => item.read_at === null)

  const refresh = useCallback(async () => {
    try {
      setItems(await listNotifications())
      setError(null)
    } catch {
      setError('Notifications indisponibles.')
    }
  }, [])

  useEffect(() => {
    void refresh()
    const timer = window.setInterval(() => {
      if (document.visibilityState === 'visible') void refresh()
    }, POLL_MS)
    return () => window.clearInterval(timer)
  }, [refresh])

  async function openItem(item: AppNotification) {
    try {
      if (item.read_at === null) await markNotificationRead(item.id)
    } catch {
      setError('Impossible de marquer la notification comme lue.')
      return
    }
    setOpen(false)
    navigate(notificationPath(item.type, role))
    void refresh()
  }

  async function markAll() {
    try {
      await Promise.all(unread.map((item) => markNotificationRead(item.id)))
    } catch {
      setError('Impossible de tout marquer comme lu.')
      return
    }
    await refresh()
  }

  return (
    <div className="relative">
      <button
        type="button"
        aria-label={`Notifications, ${unread.length} non lues`}
        aria-expanded={open}
        onClick={() => setOpen(!open)}
        className="relative rounded-[6px] p-2 text-white/65 transition-colors hover:bg-white/5 hover:text-white"
      >
        <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.7" strokeLinecap="round" strokeLinejoin="round" aria-hidden>
          <path d="M6 8a6 6 0 1112 0c0 7 3 9 3 9H3s3-2 3-9M10 21a2 2 0 004 0" />
        </svg>
        {unread.length > 0 && (
          <span className="absolute -right-0.5 -top-0.5 min-w-[1.1rem] rounded-full bg-coral px-1 text-[10px] font-semibold leading-[1.1rem] text-white">
            {unread.length}
          </span>
        )}
      </button>
      {open && (
        <div role="dialog" aria-label="Notifications" className="absolute bottom-full left-0 z-50 mb-2 w-80 max-w-[calc(100vw-2rem)] rounded-[8px] border border-line bg-white text-navy shadow-lg">
          <div className="flex items-center justify-between gap-2 border-b border-line px-4 py-3">
            <p className="text-[13.5px] font-semibold">Notifications</p>
            {unread.length > 0 && <Button size="sm" variant="discret" onClick={() => void markAll()}>Tout marquer comme lu</Button>}
          </div>
          {error && (
            <div role="alert" className="flex items-center justify-between gap-2 px-4 py-3 text-[13px] text-coral">
              {error}
              <Button size="sm" variant="discret" onClick={() => void refresh()}>Réessayer</Button>
            </div>
          )}
          {items.length === 0 && !error && <p className="px-4 py-6 text-center text-[13px] text-slate">Aucune notification.</p>}
          {items.length > 0 && (
            <ul className="max-h-96 divide-y divide-line/70 overflow-y-auto">
              {items.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => void openItem(item)}
                    className={cx('block w-full px-4 py-3 text-left hover:bg-mist', item.read_at === null && 'bg-teal/5')}
                  >
                    <span className="block text-[13.5px] font-medium text-navy">{item.title}</span>
                    <span className="block text-[12.5px] text-slate">{item.body}</span>
                    <span className="mt-1 block text-[11.5px] text-slate">{formatDateTime(item.created_at)}</span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  )
}
