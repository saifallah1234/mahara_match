// Placement: frontend/src/api/notifications.ts
import { request } from './client.ts'

export type AppNotification = {
  id: string; type: string; title: string; body: string; payload_json: Record<string, string>; read_at: string | null; created_at: string
}

/** Newest notifications only: the bell counts unread items among them. */
export const listNotifications = () =>
  request<{ results: AppNotification[] }>('/notifications/?page_size=20').then((page) => page.results)
export const markNotificationRead = (id: string) => request<AppNotification>(`/notifications/${id}/mark-read/`, { method: 'POST' })
