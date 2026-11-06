// Placement: frontend/src/lib/notifications.ts
import { ROLE_HOME } from './format.ts'
import type { RoleCode } from './types.ts'

/** Page a notification opens. Types are the stable codes sent by the owning backend services. */
const PAGE_BY_TYPE: Record<string, string> = {
  'recruitment.application.submitted': '/recruteur/candidatures',
  'recruitment.application.withdrawn': '/recruteur/candidatures',
  'recruitment.application.status_changed': '/candidat/candidatures',
  'recruitment.interview.scheduled': '/candidat/candidatures',
  'recruitment.interview.cancelled': '/candidat/candidatures',
  'training.enrollment.created': '/formation/sessions',
  'training.enrollment.cancelled': '/formation/sessions',
  'training.enrollment.status_changed': '/candidat/formations',
}

export function notificationPath(type: string, role: RoleCode): string {
  return PAGE_BY_TYPE[type] ?? ROLE_HOME[role]
}
