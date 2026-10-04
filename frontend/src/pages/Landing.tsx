import { Link } from 'react-router-dom'
import { MatchLedger } from '../components/domain'
import { Wordmark } from '../components/layout'
import { computeMatch } from '../lib/matching'
import { CANDIDATE_PROFILES, JOB_OFFERS } from '../data/seed'
import { SKILLS } from '../data/referentials'

const ACTORS = [
  { role: 'Chercheur d’emploi', detail: 'Profil, CV ATS, offres recommandées, suivi des candidatures, formations.' },
  { role: 'Employeur / Recruteur', detail: 'Espace entreprise et filiales, offres, présélection expliquée, entretiens.' },
  { role: 'Organisme de formation', detail: 'Catalogue, sessions, inscriptions, suivi des compétences acquises.' },
  { role: 'Responsable du ministère', detail: 'Tableaux de bord nationaux et régionaux, statistiques exportables.' },
  { role: 'Administrateur', detail: 'Comptes, rôles, référentiels, modération et journaux d’audit.' },
]

const AUTOMATED = [
  'Recherche et filtrage des offres',
  'Extraction et structuration du CV',
  'Score de correspondance expliqué',
  'Rédaction de messages de candidature',
  'Suivi des statuts et notifications',
]

const HUMAN = [
  'Valider les informations de son profil',
  'Confirmer chaque candidature envoyée',
  'Présélectionner ou refuser un dossier',
  'Décider : candidat et employeur',
]

export default function Landing() {
  const profile = CANDIDATE_PROFILES[0]
  const offer = JOB_OFFERS[0]
  const match = computeMatch(profile, offer, SKILLS)

  return (
    <div className="min-h-screen">
      {/* En-tête */}
      <header className="bg-navy">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-5 py-4 sm:px-8">
          <Wordmark />
          <Link
            to="/connexion"
            className="rounded-[6px] bg-teal px-4 py-2 text-sm font-medium text-white transition-colors hover:bg-teal-deep"
          >
            Ouvrir la démonstration
          </Link>
        </div>
      </header>

      {/* Héros : le calcul lui-même, pas une promesse */}
      <section className="grid-veil bg-navy">
        <div className="mx-auto grid max-w-6xl gap-10 px-5 pb-16 pt-10 sm:px-8 lg:grid-cols-[1.05fr_1fr] lg:items-center lg:gap-14 lg:pb-20">
          <div>
            <p className="text-[13px] text-cyan">Plateforme nationale · emploi, compétences et formation</p>
            <h1 className="mt-3 text-[34px] leading-[1.1] text-white sm:text-[42px]">
              Un score de correspondance que l’on peut refaire à la main.
            </h1>
            <p className="mt-4 max-w-xl text-[15px] leading-relaxed text-white/70">
              Mahara Match relie chercheurs d’emploi, employeurs, formateurs et ministère autour des compétences
              réelles. L’IA prépare et explique ; la décision reste humaine.
            </p>
            <div className="mt-7 flex flex-wrap gap-3">
              <Link
                to="/connexion"
                className="rounded-[6px] bg-teal px-5 py-2.5 text-sm font-medium text-white transition-colors hover:bg-teal-deep"
              >
                Entrer dans la plateforme
              </Link>
              <a
                href="#acteurs"
                className="rounded-[6px] border border-white/25 px-5 py-2.5 text-sm font-medium text-white transition-colors hover:border-cyan hover:text-cyan"
              >
                Voir les cinq espaces
              </a>
            </div>
            <p className="mt-6 text-[12px] text-white/45">
              Faculté des Sciences de Bizerte · 2026–2027 · données de démonstration
            </p>
          </div>

          <div>
            <p className="mb-3 text-[13px] text-white/60">
              Offre OF-218 · Développeur junior, Ariana — profil d’Emna Khelifi
            </p>
            <MatchLedger match={match} compact />
            <p className="mt-3 text-[12px] leading-relaxed text-white/55">
              Docker n’apparaît pas dans le profil. La plateforme le signale et propose les formations qui enseignent
              cette compétence, plutôt que d’écarter la candidature.
            </p>
          </div>
        </div>
      </section>

      {/* Le partage des rôles entre machine et humain */}
      <section className="border-b border-line bg-white">
        <div className="mx-auto max-w-6xl px-5 py-14 sm:px-8">
          <h2 className="text-[26px] text-navy">L’IA prépare, l’humain décide</h2>
          <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-slate">
            Mahara Match n’automatise pas la décision de recrutement. Il automatise le répétitif et rend chaque
            recommandation vérifiable.
          </p>

          <div className="mt-8 grid gap-5 sm:grid-cols-2">
            <div className="rounded-[10px] border border-line bg-mist/40 p-5">
              <h3 className="text-[14px] font-semibold text-navy">Automatisé par la plateforme</h3>
              <ul className="mt-3 space-y-2">
                {AUTOMATED.map((item) => (
                  <li key={item} className="flex gap-2.5 text-[13.5px] text-navy">
                    <svg width="15" height="15" viewBox="0 0 16 16" fill="none" className="mt-1 shrink-0 text-teal" aria-hidden>
                      <path d="M3 8.5l3 3 7-8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>
            </div>

            <div className="rounded-[10px] border-2 border-navy/12 bg-white p-5">
              <h3 className="text-[14px] font-semibold text-navy">Reste entre des mains humaines</h3>
              <ul className="mt-3 space-y-2">
                {HUMAN.map((item) => (
                  <li key={item} className="flex gap-2.5 text-[13.5px] text-navy">
                    <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
                    {item}
                  </li>
                ))}
              </ul>
            </div>
          </div>
        </div>
      </section>

      {/* Les six espaces */}
      <section id="acteurs" className="bg-cream">
        <div className="mx-auto max-w-6xl px-5 py-14 sm:px-8">
          <h2 className="text-[26px] text-navy">Une plateforme, cinq acteurs</h2>
          <p className="mt-2 max-w-2xl text-[14px] leading-relaxed text-slate">
            Chacun trouve son espace, tous partagent la même vérité sur un dossier.
          </p>

          <ul className="mt-8 grid gap-px overflow-hidden rounded-[10px] border border-line bg-line sm:grid-cols-2 lg:grid-cols-3">
            {ACTORS.map((actor) => (
              <li key={actor.role} className="bg-white p-5">
                <h3 className="text-[14px] font-semibold text-navy">{actor.role}</h3>
                <p className="mt-1.5 text-[13px] leading-relaxed text-slate">{actor.detail}</p>
              </li>
            ))}
          </ul>

          <div className="mt-10 rounded-[10px] border border-line bg-white p-6">
            <h3 className="text-[16px] font-semibold text-navy">Ce qui ne bouge pas, quel que soit l’espace</h3>
            <ul className="mt-4 grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {[
                ['Accès par rôles', 'Permissions par rôle et par organisation.'],
                ['Confirmation', 'Aucune action externe sans accord explicite.'],
                ['Sources citées', 'Chaque explication renvoie à ce qui l’a produite.'],
                ['Journal d’audit', 'Opérations sensibles tracées, agent compris.'],
              ].map(([title, detail]) => (
                <li key={title}>
                  <p className="text-[13.5px] font-medium text-navy">{title}</p>
                  <p className="mt-0.5 text-[12.5px] leading-relaxed text-slate">{detail}</p>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <footer className="border-t border-line bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-4 px-5 py-6 sm:px-8">
          <Wordmark tone="sombre" />
          <p className="text-[12px] text-slate">
            Projet académique · Faculté des Sciences de Bizerte · Ibn Hadj Mbarek Saif Allah · Chakroun Yasmine · Arbi
            Aya · Gorrab Yasmine · Tlili Malek
          </p>
        </div>
      </footer>
    </div>
  )
}
