import { useRef, useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Input, Panel } from '../../components/ui'
import { Citations } from '../../components/domain'
import { useStore } from '../../state/store'
import { computeMatch, rankOffers } from '../../lib/matching'
import { cx, formatSalary } from '../../lib/format'
import type { AgentLocale, Citation, ConversationMessage } from '../../lib/types'

const LOCALES: Array<{ id: AgentLocale; label: string; dir: 'ltr' | 'rtl' }> = [
  { id: 'fr', label: 'Français', dir: 'ltr' },
  { id: 'ar', label: 'العربية', dir: 'rtl' },
  { id: 'tn', label: 'تونسي', dir: 'rtl' },
]

const SUGGESTIONS: Record<AgentLocale, string[]> = {
  fr: [
    'Pourquoi cette offre me correspond ?',
    'Quelle est la rémunération de l’offre OF-218 ?',
    'Prépare ma candidature pour le poste de développeur junior',
  ],
  ar: ['لماذا تناسبني هذه الوظيفة؟', 'ما هو الأجر في العرض OF-218؟', 'جهّز لي ترشّحي لوظيفة مطوّر مبتدئ'],
  tn: ['علاش هالخدمة تجيني؟', 'شنوة الخلاص في العرض OF-218؟', 'حضّرلي الترشّح متاعي'],
}

let seq = 0
const newId = () => `msg-${seq++}`

export default function CandidatAssistant() {
  const { currentProfile, offers, skills, organizationOf, cvs, applications, apply } = useStore()
  const [locale, setLocale] = useState<AgentLocale>('fr')
  const [input, setInput] = useState('')
  const [messages, setMessages] = useState<ConversationMessage[]>([])
  const [thinking, setThinking] = useState(false)
  const endRef = useRef<HTMLDivElement>(null)

  if (!currentProfile) return null

  const target = offers.find((o) => o.id === 'of-218')
  const primaryCV = cvs.find((c) => c.candidateId === currentProfile.id && c.isPrimary)
  const dir = LOCALES.find((l) => l.id === locale)?.dir ?? 'ltr'

  function push(message: ConversationMessage) {
    setMessages((list) => [...list, message])
    setTimeout(() => endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }), 60)
  }

  function answer(question: string) {
    if (!target) return
    const match = computeMatch(currentProfile!, target, skills)
    const organization = organizationOf(target.organizationId)
    const lower = question.toLowerCase()

    const sources: Citation[] = [
      { label: 'Offre', reference: target.reference },
      { label: 'Profil validé', reference: `v${primaryCV?.versionNumber ?? 1}` },
    ]

    // Donnée absente : elle est signalée, jamais inventée.
    if (lower.includes('rémunér') || lower.includes('salaire') || lower.includes('أجر') || lower.includes('خلاص')) {
      const stated = target.minSalary != null || target.maxSalary != null
      push({
        id: newId(),
        sender: 'AGENT',
        createdAt: new Date().toISOString(),
        content: stated
          ? `L’offre ${target.reference} indique une rémunération de ${formatSalary(target.minSalary, target.maxSalary)}.`
          : `L’offre ${target.reference} ne renseigne pas de rémunération. Je ne peux pas l’estimer : l’information n’existe pas dans la fiche.`,
        citations: sources,
      })
      return
    }

    // Préparation d'une action : récapitulatif, puis confirmation explicite.
    if (lower.includes('prépare') || lower.includes('candidat') || lower.includes('ترشّح') || lower.includes('حضّر')) {
      const draft =
        'Je couvre SQL et Python, les deux compétences obligatoires de ce poste. Mon stage de fin d’études portait sur un tableau de bord de production alimenté par des requêtes SQL. Docker ne figure pas encore dans mon profil : je suis inscrite à une formation qui démarre le 20 octobre.'
      push({
        id: newId(),
        sender: 'AGENT',
        createdAt: new Date().toISOString(),
        content: `J’ai préparé un message à partir de vos expériences confirmées. Voici le récapitulatif avant envoi — rien n’est transmis sans votre accord.`,
        citations: sources,
        action: {
          type: 'POSTULER',
          offerId: target.id,
          cvId: primaryCV?.id ?? '',
          coverLetter: draft,
          status: 'PROPOSED',
        },
      })
      return
    }

    // Explication du matching, fondée sur le calcul réel.
    const covered = match.lines.filter((l) => l.state === 'COUVERTE').map((l) => l.skillName)
    const missing = match.lines.filter((l) => l.state !== 'COUVERTE').map((l) => l.skillName)

    const content =
      locale === 'fr'
        ? `Pour l’offre ${target.reference} — ${target.title} chez ${organization?.legalName} — vous couvrez ${covered.join(' et ')} (obligatoires). ${missing.length > 0 ? `${missing.join(' et ')} n’apparaît pas dans votre profil.` : ''} Le calcul donne ${match.formula}, soit ${match.earnedPoints} points sur ${match.totalPoints}. Ce score mesure la couverture des compétences demandées, pas une probabilité d’embauche.`
        : locale === 'ar'
          ? `بالنسبة للعرض ${target.reference} لدى ${organization?.legalName}، أنت تغطّين ${covered.join(' و')} وهما إجباريتان. ${missing.length > 0 ? `${missing.join(' و')} غير موجودة في ملفّك.` : ''} النتيجة: ${match.formula} أي ${match.earnedPoints} من ${match.totalPoints} نقاط.`
          : `في العرض ${target.reference} متاع ${organization?.legalName}، عندك ${covered.join(' و')} وهوما إجباريين. ${missing.length > 0 ? `${missing.join(' و')} ما ثماش في البروفيل متاعك.` : ''} الحساب يعطي ${match.formula}، يعني ${match.earnedPoints} من ${match.totalPoints}.`

    push({ id: newId(), sender: 'AGENT', createdAt: new Date().toISOString(), content, citations: sources })
  }

  function send(text: string) {
    const question = text.trim()
    if (!question) return
    push({ id: newId(), sender: 'USER', content: question, createdAt: new Date().toISOString() })
    setInput('')
    setThinking(true)
    setTimeout(() => {
      setThinking(false)
      answer(question)
    }, 650)
  }

  /** Les droits et l'ouverture de l'offre sont revérifiés au moment du clic. */
  function confirmAction(messageId: string) {
    const message = messages.find((m) => m.id === messageId)
    if (!message?.action) return
    const result = apply(message.action.offerId, message.action.cvId, message.action.coverLetter)

    setMessages((list) =>
      list.map((m) =>
        m.id === messageId && m.action
          ? {
              ...m,
              action: {
                ...m.action,
                status: result.ok ? 'CONFIRMED' : 'BLOCKED',
                blockedReason: result.ok ? undefined : result.message,
              },
            }
          : m,
      ),
    )

    push({
      id: newId(),
      sender: 'AGENT',
      createdAt: new Date().toISOString(),
      content: result.ok
        ? 'La candidature est déposée. Le recruteur a été notifié et le dossier apparaît dans votre suivi au statut « Soumise ».'
        : `Le dépôt n’a pas eu lieu. ${result.message}`,
    })
  }

  function cancelAction(messageId: string) {
    setMessages((list) =>
      list.map((m) => (m.id === messageId && m.action ? { ...m, action: { ...m.action, status: 'CANCELLED' } } : m)),
    )
    push({
      id: newId(),
      sender: 'AGENT',
      createdAt: new Date().toISOString(),
      content: 'Proposition annulée. Aucune candidature n’a été envoyée.',
    })
  }

  const bestMatch = rankOffers(currentProfile, offers, skills)[0]

  return (
    <>
      <PageHeader
        title="Assistant"
        action={
          <div className="flex gap-1 rounded-[6px] border border-line bg-white p-0.5">
            {LOCALES.map((l) => (
              <button
                key={l.id}
                onClick={() => setLocale(l.id)}
                className={cx(
                  'rounded-[4px] px-3 py-1.5 text-[13px] font-medium transition-colors',
                  locale === l.id ? 'bg-teal text-white' : 'text-slate hover:text-navy',
                )}
              >
                {l.label}
              </button>
            ))}
          </div>
        }
      />

      <PageBody className="space-y-5">
        <div className="grid gap-5 lg:grid-cols-[1fr_300px] lg:items-start">
          <Panel className="flex min-h-[60vh] flex-col">
            <div className="flex-1 space-y-4 px-5 py-5" dir={dir}>
              {messages.length === 0 && (
                <div className="py-8 text-center" dir="ltr">
                  <p className="text-[14px] font-medium text-navy">Posez votre question</p>
                  <p className="mx-auto mt-1 max-w-sm text-[13px] leading-relaxed text-slate">
                    En français, en arabe ou en tunisien. Les réponses s’appuient uniquement sur les données auxquelles
                    vous avez accès.
                  </p>
                </div>
              )}

              {messages.map((message) => (
                <div key={message.id} className={cx('flex', message.sender === 'USER' ? 'justify-end' : 'justify-start')}>
                  <div
                    className={cx(
                      'max-w-[85%] rounded-[10px] px-4 py-3',
                      message.sender === 'USER' ? 'bg-teal text-white' : 'border border-line bg-mist/40',
                    )}
                  >
                    <p className="text-[13.5px] leading-relaxed">{message.content}</p>
                    {message.citations && <Citations items={message.citations} />}

                    {message.action && (
                      <div className="mt-3 rounded-[8px] border border-line bg-white p-3.5" dir="ltr">
                        <p className="text-[12px] font-semibold text-navy">Récapitulatif avant envoi</p>
                        <dl className="mt-2 space-y-1 text-[12.5px]">
                          <div className="flex justify-between gap-3">
                            <dt className="text-slate">Entreprise</dt>
                            <dd className="text-right font-medium text-navy">
                              {organizationOf(target?.organizationId)?.legalName}
                            </dd>
                          </div>
                          <div className="flex justify-between gap-3">
                            <dt className="text-slate">Offre</dt>
                            <dd className="text-right font-medium text-navy">
                              {target?.title} ({target?.reference})
                            </dd>
                          </div>
                          <div className="flex justify-between gap-3">
                            <dt className="text-slate">CV transmis</dt>
                            <dd className="text-right font-medium text-navy">v{primaryCV?.versionNumber}</dd>
                          </div>
                        </dl>
                        <p className="mt-2.5 rounded-[6px] bg-mist/60 p-2.5 text-[12.5px] leading-relaxed text-navy">
                          {message.action.coverLetter}
                        </p>

                        {message.action.status === 'PROPOSED' && (
                          <div className="mt-3 flex gap-2">
                            <Button size="sm" onClick={() => confirmAction(message.id)}>
                              Confirmer l’envoi
                            </Button>
                            <Button size="sm" variant="secondaire" onClick={() => cancelAction(message.id)}>
                              Annuler
                            </Button>
                          </div>
                        )}
                        {message.action.status === 'CONFIRMED' && (
                          <p className="mt-3">
                            <Badge tone="positif">Candidature envoyée</Badge>
                          </p>
                        )}
                        {message.action.status === 'CANCELLED' && (
                          <p className="mt-3">
                            <Badge tone="neutre">Annulée — rien n’a été envoyé</Badge>
                          </p>
                        )}
                        {message.action.status === 'BLOCKED' && (
                          <p className="mt-3">
                            <Badge tone="negatif">Bloquée — {message.action.blockedReason}</Badge>
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {thinking && <p className="text-[13px] text-slate">L’assistant consulte vos données…</p>}
              <div ref={endRef} />
            </div>

            {messages.length === 0 && (
              <div className="flex flex-wrap gap-2 border-t border-line px-5 py-3">
                {SUGGESTIONS[locale].map((suggestion) => (
                  <button
                    key={suggestion}
                    onClick={() => send(suggestion)}
                    dir={dir}
                    className="rounded-[6px] border border-line px-3 py-1.5 text-[12.5px] text-navy transition-colors hover:border-teal hover:text-teal"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            )}

            <form
              onSubmit={(e) => {
                e.preventDefault()
                send(input)
              }}
              className="flex gap-2 border-t border-line px-5 py-3.5"
            >
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                dir={dir}
                placeholder={locale === 'fr' ? 'Écrivez votre question…' : 'اكتب سؤالك…'}
                aria-label="Votre question"
              />
              <Button type="submit" disabled={!input.trim()}>
                Envoyer
              </Button>
            </form>
          </Panel>

          <div className="space-y-4">
            <Panel title="Ce que l’assistant garantit">
              <ul className="space-y-2.5 px-5 py-4">
                {[
                  'Réponses fondées sur vos données, sources citées',
                  'Donnée absente ? Elle est signalée, jamais inventée',
                  'Aucune action sans confirmation explicite',
                  'Droits revérifiés juste avant l’exécution',
                  'Aucune requête libre générée sur la base',
                ].map((item) => (
                  <li key={item} className="flex gap-2.5 text-[13px] text-navy">
                    <svg width="14" height="14" viewBox="0 0 16 16" fill="none" className="mt-1 shrink-0 text-teal" aria-hidden>
                      <path d="M3 8.5l3 3 7-8" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" />
                    </svg>
                    {item}
                  </li>
                ))}
              </ul>
            </Panel>

            {bestMatch && (
              <Panel title="Contexte de la conversation">
                <div className="px-5 py-4 text-[13px]">
                  <p className="text-slate">L’assistant peut consulter :</p>
                  <ul className="mt-2 space-y-1 text-navy">
                    <li>· votre profil validé</li>
                    <li>· vos {cvs.filter((c) => c.candidateId === currentProfile.id).length} versions de CV</li>
                    <li>· les {offers.filter((o) => o.status === 'PUBLISHED').length} offres ouvertes</li>
                    <li>· vos {applications.filter((a) => a.candidateId === currentProfile.id).length} candidatures</li>
                  </ul>
                </div>
              </Panel>
            )}

          </div>
        </div>
      </PageBody>
    </>
  )
}
