import { useNavigate } from 'react-router-dom'
import { Wordmark } from '../components/layout'
import { useStore } from '../state/store'
import { ROLE_HOME, ROLE_LABEL } from '../lib/format'
import type { RoleCode, UUID } from '../lib/types'

/** Comptes de démonstration : un par rôle, pour parcourir chaque espace. */
const ACCOUNTS: Array<{ userId: UUID; role: RoleCode; name: string; context: string }> = [
  { userId: 'u-emna', role: 'CANDIDATE', name: 'Emna Khelifi', context: 'Jeune diplômée, Bizerte — 3 candidatures en cours' },
  { userId: 'u-sofiane', role: 'RECRUITER', name: 'Sofiane Mabrouk', context: 'TelNet Ariana — 4 offres publiées' },
  { userId: 'u-leila', role: 'TRAINING_MANAGER', name: 'Leila Ferchichi', context: 'Code Line Academy — 4 programmes' },
  { userId: 'u-nadia', role: 'MINISTRY_MANAGER', name: 'Nadia Bouzid', context: 'Ministère — indicateurs nationaux' },
  { userId: 'u-admin', role: 'ADMIN', name: 'Rania Saidi', context: 'Administration de la plateforme' },
]

export default function SignIn() {
  const { signIn } = useStore()
  const navigate = useNavigate()

  function enter(userId: UUID, role: RoleCode) {
    signIn(userId, role)
    navigate(ROLE_HOME[role])
  }

  return (
    <div className="flex min-h-screen flex-col bg-navy">
      <header className="mx-auto w-full max-w-3xl px-5 py-6 sm:px-8">
        <a href="/" onClick={(e) => { e.preventDefault(); navigate('/') }}>
          <Wordmark />
        </a>
      </header>

      <main className="mx-auto w-full max-w-3xl flex-1 px-5 pb-12 sm:px-8">
        <h1 className="text-[26px] text-white">Choisissez un espace</h1>
        <p className="mt-2 max-w-xl text-[14px] leading-relaxed text-white/65">
          La démonstration ouvre directement l’espace du rôle sélectionné, avec un jeu de données fictives cohérent
          entre tous les acteurs. Vous pouvez changer d’espace à tout moment depuis le menu.
        </p>

        <ul className="mt-8 grid gap-px overflow-hidden rounded-[10px] bg-white/10 sm:grid-cols-2">
          {ACCOUNTS.map((account) => (
            <li key={account.userId}>
              <button
                onClick={() => enter(account.userId, account.role)}
                className="group flex h-full w-full flex-col gap-1 bg-navy px-5 py-4 text-left transition-colors hover:bg-navy-soft"
              >
                <span className="text-[13px] text-cyan">{ROLE_LABEL[account.role]}</span>
                <span className="text-[15px] font-medium text-white">{account.name}</span>
                <span className="text-[12.5px] leading-relaxed text-white/55">{account.context}</span>
              </button>
            </li>
          ))}
        </ul>

        <p className="mt-6 text-[12px] leading-relaxed text-white/45">
          En production, cet écran est remplacé par une authentification par e-mail et mot de passe, ou par un
          fournisseur d’identité externe. Les permissions restent portées par les rôles et l’organisation de
          rattachement.
        </p>
      </main>
    </div>
  )
}
