import { useState, type ReactNode } from 'react'
import { Link, NavLink, Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../state/auth'
import { ROLE_HOME, ROLE_LABEL, cx, initials } from '../lib/format'
import type { RoleCode } from '../lib/types'

/* ------------------------------------------------------------------ */
/* Marque                                                              */
/* ------------------------------------------------------------------ */

export function Wordmark({ tone = 'clair' }: { tone?: 'clair' | 'sombre' }) {
  return (
    <span className="flex items-center gap-2.5">
      <svg width="24" height="24" viewBox="0 0 24 24" fill="none" aria-hidden>
        <rect width="24" height="24" rx="6" fill={tone === 'clair' ? '#0E7C86' : '#fff'} />
        <path
          d="M6 17V8l6 5 6-5v9"
          stroke={tone === 'clair' ? '#7FE0E6' : '#0E7C86'}
          strokeWidth="2"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      <span className={cx('text-[15px] font-semibold tracking-tight', tone === 'clair' ? 'text-white' : 'text-navy')}>
        Mahara Match
      </span>
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* Icônes                                                              */
/* ------------------------------------------------------------------ */

const PATHS: Record<string, string> = {
  dashboard: 'M3 3h7v7H3zM14 3h7v4h-7zM14 11h7v10h-7zM3 14h7v7H3z',
  profile: 'M12 12a4 4 0 100-8 4 4 0 000 8zM4 21v-1a6 6 0 016-6h4a6 6 0 016 6v1',
  cv: 'M6 2h8l5 5v15H6zM14 2v5h5M9 13h7M9 17h5',
  search: 'M11 19a8 8 0 100-16 8 8 0 000 16zM21 21l-4.3-4.3',
  applications: 'M4 4h16v5H4zM4 13h16v7H4zM8 16h6',
  training: 'M12 3l9 5-9 5-9-5 9-5zM5 11v5c0 1.7 3.1 3 7 3s7-1.3 7-3v-5',
  assistant: 'M4 5h16v11H9l-5 4V5zM9 10h.01M13 10h.01M17 10h.01',
  company: 'M4 21V7l7-4 7 4v14M9 21v-5h6v5M9 11h.01M15 11h.01',
  offers: 'M4 7h16v13H4zM8 7V4h8v3M9 13h6',
  interview: 'M8 2v4M16 2v4M3 9h18M5 5h14v16H5z',
  people: 'M9 11a3.5 3.5 0 100-7 3.5 3.5 0 000 7zM2 20v-1a5 5 0 015-5h4a5 5 0 015 5v1M17 7.5a3 3 0 010 6M19 20v-1a4.5 4.5 0 00-2-3.7',
  check: 'M4 12l5 5L20 6',
  stats: 'M4 20V10M10 20V4M16 20v-7M22 20H2',
  accounts: 'M12 11a4 4 0 100-8 4 4 0 000 8zM3 21v-1a5 5 0 015-5h3M17 21l2 2 4-4',
  referential: 'M4 6h16M4 12h16M4 18h10M18 16l2 2 3-3',
  imports: 'M12 3v12M8 11l4 4 4-4M4 19h16',
  audit: 'M9 3h8l4 4v14H9zM13 3v5h5M3 7v14h6',
  logout: 'M15 4h4v16h-4M11 16l4-4-4-4M3 12h12',
}

export function Icon({ name, size = 17 }: { name: keyof typeof PATHS | string; size?: number }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.7"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
      className="shrink-0"
    >
      <path d={PATHS[name] ?? PATHS.dashboard} />
    </svg>
  )
}

/* ------------------------------------------------------------------ */
/* Navigation par rôle                                                 */
/* ------------------------------------------------------------------ */

interface NavItem {
  to: string
  label: string
  icon: string
  end?: boolean
}

export const NAVIGATION: Record<RoleCode, NavItem[]> = {
  CANDIDATE: [
    { to: '/candidat', label: 'Tableau de bord', icon: 'dashboard', end: true },
    { to: '/candidat/profil', label: 'Mon profil', icon: 'profile' },
    { to: '/candidat/cv', label: 'Mes CV', icon: 'cv' },
    { to: '/candidat/offres', label: 'Offres', icon: 'search' },
    { to: '/candidat/candidatures', label: 'Mes candidatures', icon: 'applications' },
    { to: '/candidat/formations', label: 'Formations', icon: 'training' },
        { to: '/candidat/assistant', label: 'Assistant', icon: 'assistant' },
    { to: '/candidat/entretiens-blancs', label: 'Entretiens blancs', icon: 'interview' },
  ],
  RECRUITER: [
    { to: '/recruteur', label: 'Tableau de bord', icon: 'dashboard', end: true },
    { to: '/recruteur/entreprise', label: 'Mon entreprise', icon: 'company' },
    { to: '/recruteur/offres', label: 'Mes offres', icon: 'offers' },
    { to: '/recruteur/candidatures', label: 'Candidatures', icon: 'applications' },
    { to: '/recruteur/entretiens', label: 'Entretiens', icon: 'interview' },
  ],
  TRAINING_MANAGER: [
    { to: '/formation', label: 'Tableau de bord', icon: 'dashboard', end: true },
    { to: '/formation/programmes', label: 'Programmes', icon: 'training' },
    { to: '/formation/sessions', label: 'Sessions', icon: 'interview' },
    { to: '/formation/organisme', label: 'Mon organisme', icon: 'company' },
  ],
  MINISTRY_MANAGER: [
    { to: '/ministere', label: 'Indicateurs', icon: 'stats', end: true },
  ],
  ADMIN: [
    { to: '/admin', label: 'Tableau de bord', icon: 'dashboard', end: true },
    { to: '/admin/comptes', label: 'Comptes et rôles', icon: 'accounts' },
    { to: '/admin/demandes', label: 'Demandes d’accès', icon: 'people' },
    { to: '/admin/organisations', label: 'Organisations', icon: 'company' },
    { to: '/admin/referentiels', label: 'Référentiels', icon: 'referential' },
    { to: '/admin/imports', label: 'Imports', icon: 'imports' },
    { to: '/admin/audit', label: 'Journal d’audit', icon: 'audit' },
  ],
}

/* ------------------------------------------------------------------ */
/* Coquille applicative                                                */
/* ------------------------------------------------------------------ */

export function AppShell() {
  const { user, workspace, logout } = useAuth()
  const [menuOpen, setMenuOpen] = useState(false)
  const location = useLocation()

  if (!user || !workspace) return <Navigate to="/connexion" replace state={{ from: location.pathname }} />

  const role = workspace.role_code
  const items = NAVIGATION[role]

  return (
    <div className="flex min-h-screen">
      {/* Le rail reste identique pour tous les rôles : une plateforme,
          une même vérité. C'est la puce qui identifie l'espace. */}
      <aside
        className={cx(
          'fixed inset-y-0 left-0 z-40 flex w-64 flex-col bg-navy transition-transform lg:static lg:translate-x-0',
          menuOpen ? 'translate-x-0' : '-translate-x-full',
        )}
      >
        <div className="px-5 py-5">
          <Link to={ROLE_HOME[role]} onClick={() => setMenuOpen(false)}>
            <Wordmark />
          </Link>
          <p className="mt-3 inline-flex rounded-[4px] bg-white/8 px-2 py-1 text-[11px] font-medium text-cyan">
            {ROLE_LABEL[role]}
          </p>
        </div>

        <nav className="flex-1 space-y-0.5 overflow-y-auto px-3">
          {items.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setMenuOpen(false)}
              className={({ isActive }) =>
                cx(
                  'flex items-center gap-3 rounded-[6px] px-3 py-2 text-[13.5px] transition-colors',
                  isActive ? 'bg-white/10 font-medium text-white' : 'text-white/65 hover:bg-white/5 hover:text-white',
                )
              }
            >
              <Icon name={item.icon} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-white/10 px-3 py-3">
          <div className="flex items-center gap-3 px-2 py-1.5">
            <span className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-teal text-[12px] font-semibold text-white">
              {initials(user.first_name, user.last_name)}
            </span>
            <span className="min-w-0 flex-1">
              <span className="block truncate text-[13px] text-white">
                {user.first_name} {user.last_name}
              </span>
              <span className="block truncate text-[11px] text-white/50">{user.email}</span>
            </span>
          </div>
          {user.workspaces.length > 1 && <Link className="mt-1 block px-3 py-2 text-[13px] text-cyan" to="/espaces">Changer d’espace</Link>}
          <button
            onClick={() => void logout().catch(() => {})}
            className="mt-1 flex w-full items-center gap-3 rounded-[6px] px-3 py-2 text-[13px] text-white/65 transition-colors hover:bg-white/5 hover:text-white"
          >
            <Icon name="logout" />
            Se déconnecter
          </button>
        </div>
      </aside>

      {menuOpen && (
        <button
          aria-label="Fermer le menu"
          onClick={() => setMenuOpen(false)}
          className="fixed inset-0 z-30 bg-navy/40 lg:hidden"
        />
      )}

      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex items-center gap-3 border-b border-line bg-white px-4 py-3 lg:hidden">
          <button
            onClick={() => setMenuOpen(true)}
            aria-label="Ouvrir le menu"
            className="rounded-[6px] p-1.5 text-navy hover:bg-mist"
          >
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" aria-hidden>
              <path d="M4 7h16M4 12h16M4 17h16" strokeLinecap="round" />
            </svg>
          </button>
          <Wordmark tone="sombre" />
        </header>

        <main className="flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* En-tête de page                                                     */
/* ------------------------------------------------------------------ */

export function PageHeader({
  title,
  description,
  action,
  back,
}: {
  title: string
  description?: ReactNode
  action?: ReactNode
  back?: { to: string; label: string }
}) {
  return (
    <header className="border-b border-line bg-white px-5 py-5 sm:px-8">
      <div className="mx-auto max-w-6xl">
        {back && (
          <Link to={back.to} className="mb-2 inline-flex items-center gap-1.5 text-[13px] text-slate hover:text-teal">
            <svg width="14" height="14" viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.6" aria-hidden>
              <path d="M10 3L5 8l5 5" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
            {back.label}
          </Link>
        )}
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0">
            <h1 className="text-[22px] font-semibold text-navy">{title}</h1>
            {description && <p className="mt-1 max-w-2xl text-[13.5px] leading-relaxed text-slate">{description}</p>}
          </div>
          {action && <div className="flex shrink-0 flex-wrap gap-2">{action}</div>}
        </div>
      </div>
    </header>
  )
}

export function PageBody({ children, className }: { children: ReactNode; className?: string }) {
  return <div className={cx('mx-auto max-w-6xl px-5 py-6 sm:px-8', className)}>{children}</div>
}
