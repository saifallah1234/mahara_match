import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { Icon, Wordmark } from './layout'
import { Panel } from './ui'

export function AuthLayout({ title, description, children }: {
  title: string
  description: string
  children: ReactNode
}) {
  return (
    <div className="min-h-screen bg-cream">
      <header className="bg-navy">
        <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-5 py-5 sm:px-8">
          <Link to="/" aria-label="Mahara Match — accueil"><Wordmark /></Link>
          <Link to="/" className="text-sm text-cyan hover:underline">Retour à l’accueil</Link>
        </div>
      </header>
      <main className="mx-auto grid max-w-6xl items-center gap-8 px-5 py-8 sm:px-8 sm:py-12 lg:min-h-[calc(100vh-76px)] lg:grid-cols-2 lg:gap-16">
        <aside className="grid-veil hidden rounded-[20px] bg-navy p-10 text-white lg:block">
          <p className="text-[13px] font-medium text-cyan">Emploi · compétences · formation</p>
          <h2 className="mt-5 text-[36px] leading-tight">Votre prochain chapitre commence ici.</h2>
          <p className="mt-5 text-[15px] leading-relaxed text-white/70">
            Un même compte pour retrouver vos opportunités et les espaces auxquels vous avez accès.
          </p>
          <ul className="mt-10 space-y-6">
            {[
              ['profile', 'Valorisez votre parcours', 'Profil, compétences et candidatures réunis.'],
              ['company', 'Retrouvez votre organisation', 'Recrutement et formation dans un espace dédié.'],
              ['check', 'Gardez la maîtrise de vos accès', 'Vos espaces sont attribués selon vos droits.'],
            ].map(([icon, heading, detail]) => (
              <li key={icon} className="flex items-start gap-4">
                <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-[10px] bg-white/10 text-cyan"><Icon name={icon} size={20} /></span>
                <div><p className="text-sm font-medium">{heading}</p><p className="mt-1 text-[13px] text-white/60">{detail}</p></div>
              </li>
            ))}
          </ul>
        </aside>
        <div className="mx-auto w-full max-w-lg">
          <Panel className="overflow-hidden shadow-lift">
            <div className="h-1 bg-teal" />
            <div className="p-6 sm:p-8">
              <h1 className="text-[28px] text-navy">{title}</h1>
              <p className="mt-2 text-sm leading-relaxed text-slate">{description}</p>
              <div className="mt-7">{children}</div>
            </div>
          </Panel>
          <p className="mt-5 text-center text-[12px] text-slate">Mahara Match · Des compétences aux opportunités</p>
        </div>
      </main>
    </div>
  )
}
