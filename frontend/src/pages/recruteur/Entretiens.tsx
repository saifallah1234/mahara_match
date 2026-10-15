import { PageBody, PageHeader } from '../../components/layout'
import { Badge, EmptyState, Panel } from '../../components/ui'
import { StatusPill } from '../../components/domain'
import { useStore } from '../../state/store'
import { formatDateTime } from '../../lib/format'
import type { InterviewStatus, InterviewType } from '../../lib/types'

const TYPE_LABEL: Record<InterviewType, string> = {
  TELEPHONE: 'Téléphonique',
  VISIO: 'Visioconférence',
  PRESENTIEL: 'Présentiel',
}

const STATUS_TONE: Record<InterviewStatus, 'encours' | 'positif' | 'negatif'> = {
  PLANIFIE: 'encours',
  REALISE: 'positif',
  ANNULE: 'negatif',
}

const STATUS_TEXT: Record<InterviewStatus, string> = {
  PLANIFIE: 'Planifié',
  REALISE: 'Réalisé',
  ANNULE: 'Annulé',
}

export default function RecruteurEntretiens() {
  const { session, interviews, applications, offers, profileOf, userOf } = useStore()
  if (!session) return null

  const myOffers = offers.filter((o) => o.createdBy === session.user.id)
  const mine = interviews
    .filter((interview) => {
      const application = applications.find((a) => a.id === interview.applicationId)
      return application && myOffers.some((o) => o.id === application.offerId)
    })
    .sort((a, b) => +new Date(a.scheduledAt) - +new Date(b.scheduledAt))

  const upcoming = mine.filter((i) => i.status === 'PLANIFIE')
  const past = mine.filter((i) => i.status !== 'PLANIFIE')

  function renderList(list: typeof mine) {
    return (
      <ul className="divide-y divide-line/70">
        {list.map((interview) => {
          const application = applications.find((a) => a.id === interview.applicationId)
          const offer = offers.find((o) => o.id === application?.offerId)
          const profile = application ? profileOf(application.candidateId) : undefined
          const user = profile ? userOf(profile.userId) : undefined
          return (
            <li key={interview.id} className="flex flex-wrap items-start justify-between gap-3 px-5 py-4">
              <div className="min-w-0">
                <p className="text-[14px] font-medium text-navy">
                  {user?.firstName} {user?.lastName}
                </p>
                <p className="text-[12.5px] text-slate">{offer?.title}</p>
                <p className="mt-1 text-[13px] text-navy">
                  {formatDateTime(interview.scheduledAt)} · {interview.durationMinutes} min
                </p>
                <p className="text-[12.5px] text-slate">{interview.locationOrUrl}</p>
                {interview.feedback && (
                  <p className="mt-1.5 text-[13px] leading-relaxed text-slate">{interview.feedback}</p>
                )}
              </div>
              <div className="flex shrink-0 flex-col items-end gap-1.5">
                <Badge tone={STATUS_TONE[interview.status]}>{STATUS_TEXT[interview.status]}</Badge>
                <Badge tone="neutre">{TYPE_LABEL[interview.type]}</Badge>
                {application && <StatusPill status={application.status} />}
              </div>
            </li>
          )
        })}
      </ul>
    )
  }

  return (
    <>
      <PageHeader
        title="Entretiens"
      />

      <PageBody className="space-y-6">
        <Panel title="À venir" description={`${upcoming.length} entretien${upcoming.length > 1 ? 's' : ''} planifié${upcoming.length > 1 ? 's' : ''}`}>
          {upcoming.length === 0 ? (
            <EmptyState title="Aucun entretien planifié">
              Un entretien se propose depuis un dossier présélectionné, dans le pipeline des candidatures.
            </EmptyState>
          ) : (
            renderList(upcoming)
          )}
        </Panel>

        {past.length > 0 && <Panel title="Historique">{renderList(past)}</Panel>}

      </PageBody>
    </>
  )
}
