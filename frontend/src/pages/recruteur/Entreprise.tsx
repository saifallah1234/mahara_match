import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Panel } from '../../components/ui'
import { useAuth } from '../../state/auth'
import { useRecruiter } from '../../state/recruiter'
import { MembersPanel } from '../../components/members'

const TYPE_LABEL: Record<string, string> = { COMPANY: 'Entreprise', SUBSIDIARY: 'Filiale' }

export default function RecruteurEntreprise() {
  const { user, workspace } = useAuth()
  const { offers } = useRecruiter()
  const org = workspace?.organization

  if (!org) {
    return (
      <PageBody>
        <Panel className="p-8">
          <p className="text-center text-[14px] text-slate">Aucune organisation rattachée à ce compte.</p>
        </Panel>
      </PageBody>
    )
  }

  const verified = org.verification_status === 'VERIFIED'
  const published = offers.filter((o) => o.status === 'PUBLISHED').length

  return (
    <>
      <PageHeader
        title="Mon entreprise"
        action={<Badge tone={verified ? 'positif' : 'attention'}>{verified ? 'Organisation vérifiée' : 'Vérification en attente'}</Badge>}
      />
      <PageBody className="space-y-6">
        <Panel title="Organisation">
          <dl className="grid gap-4 px-5 py-4 text-[13.5px] sm:grid-cols-3">
            <div><dt className="text-slate">Raison sociale</dt><dd className="font-medium text-navy">{org.legal_name}</dd></div>
            <div><dt className="text-slate">Type</dt><dd className="text-navy">{TYPE_LABEL[org.type] ?? org.type}</dd></div>
            <div><dt className="text-slate">Offres</dt><dd className="text-navy">{published} publiée{published > 1 ? 's' : ''} sur {offers.length}</dd></div>
          </dl>
        </Panel>
        <MembersPanel organizationId={org.id} />
        <Panel title="Mon compte">
          <dl className="grid gap-4 px-5 py-4 text-[13.5px] sm:grid-cols-2">
            <div><dt className="text-slate">Nom</dt><dd className="text-navy">{user?.first_name} {user?.last_name}</dd></div>
            <div><dt className="text-slate">E-mail</dt><dd className="text-navy">{user?.email}</dd></div>
          </dl>
        </Panel>
      </PageBody>
    </>
  )
}