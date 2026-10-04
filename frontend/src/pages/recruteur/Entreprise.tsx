import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Cell, Field, Input, Panel, Row, Table, Textarea } from '../../components/ui'
import { useStore } from '../../state/store'
import { formatDate, formatPlace } from '../../lib/format'

export default function RecruteurEntreprise() {
  const { session, organizations, organizationOf, offers, users } = useStore()
  if (!session) return null

  const mine = organizationOf(session.user.organizationId)
  const group = mine?.parentId ? organizationOf(mine.parentId) : mine
  const subsidiaries = organizations.filter((o) => o.parentId === group?.id)
  const members = users.filter((u) => u.organizationId === mine?.id)

  if (!mine || !group) {
    return (
      <PageBody>
        <Panel className="p-8">
          <p className="text-center text-[14px] text-slate">Aucune organisation rattachée à ce compte.</p>
        </Panel>
      </PageBody>
    )
  }

  return (
    <>
      <PageHeader
        title="Mon entreprise"
        action={
          <Badge tone={group.verificationStatus === 'VERIFIED' ? 'positif' : 'attention'}>
            {group.verificationStatus === 'VERIFIED' ? 'Organisation vérifiée' : 'Vérification en attente'}
          </Badge>
        }
      />

      <PageBody className="space-y-6">
        <Panel title="Structure du groupe">
          <div className="px-5 py-4">
            <div className="rounded-[8px] border border-line bg-mist/40 px-4 py-3">
              <p className="text-[14px] font-semibold text-navy">{group.legalName}</p>
              <p className="text-[12.5px] text-slate">
                Maison mère · {formatPlace(group.city, group.governorate)}
                {group.matriculeFiscal && ` · matricule fiscal ${group.matriculeFiscal}`}
              </p>
            </div>

            {subsidiaries.length > 0 && (
              <ul className="ml-5 mt-2 space-y-2 border-l border-line pl-5">
                {subsidiaries.map((sub) => {
                  const count = offers.filter((o) => o.organizationId === sub.id).length
                  return (
                    <li
                      key={sub.id}
                      className={`rounded-[8px] border px-4 py-3 ${sub.id === mine.id ? 'border-teal bg-cyan-soft/30' : 'border-line bg-white'}`}
                    >
                      <div className="flex flex-wrap items-center justify-between gap-2">
                        <div>
                          <p className="text-[13.5px] font-medium text-navy">
                            {sub.legalName}
                            {sub.id === mine.id && <span className="ml-2 text-[12px] text-teal">votre entité</span>}
                          </p>
                          <p className="text-[12.5px] text-slate">
                            {formatPlace(sub.city, sub.governorate)} · {count} offre{count > 1 ? 's' : ''}
                          </p>
                        </div>
                        <Badge tone={sub.verificationStatus === 'VERIFIED' ? 'positif' : 'attention'}>
                          {sub.verificationStatus === 'VERIFIED' ? 'Vérifiée' : 'En attente'}
                        </Badge>
                      </div>
                    </li>
                  )
                })}
              </ul>
            )}
          </div>
        </Panel>

        <Panel title="Fiche de l’entité">
          <div className="grid gap-4 p-5 sm:grid-cols-2">
            <Field label="Raison sociale" required>
              <Input defaultValue={mine.legalName} />
            </Field>
            <Field label="Matricule fiscal" required hint="13 caractères, unique.">
              <Input defaultValue={mine.matriculeFiscal} maxLength={13} />
            </Field>
            <Field label="Gouvernorat">
              <Input defaultValue={mine.governorate} />
            </Field>
            <Field label="Ville">
              <Input defaultValue={mine.city} />
            </Field>
            <Field label="Site web">
              <Input defaultValue={group.websiteUrl} placeholder="https://" />
            </Field>
            <Field label="Adresse">
              <Input defaultValue={mine.addressLine} />
            </Field>
            <div className="sm:col-span-2">
              <Field label="Présentation" hint="Visible par les candidats sur chaque offre publiée.">
                <Textarea defaultValue={group.description} rows={4} />
              </Field>
            </div>
          </div>
          <div className="flex justify-end border-t border-line px-5 py-3.5">
            <Button>Enregistrer</Button>
          </div>
        </Panel>

        <Panel title="Recruteurs rattachés">
          <Table head={['Recruteur', 'Fonction', 'Dernière connexion', 'Statut']}>
            {members.map((member) => (
              <Row key={member.id}>
                <Cell>
                  <p className="font-medium text-navy">
                    {member.firstName} {member.lastName}
                  </p>
                  <p className="text-[12.5px] text-slate">{member.email}</p>
                </Cell>
                <Cell className="text-[13px] text-slate">{member.jobTitle ?? 'Non renseignée'}</Cell>
                <Cell className="text-[13px] text-slate">{formatDate(member.lastLoginAt)}</Cell>
                <Cell>
                  <Badge tone={member.status === 'ACTIVE' ? 'positif' : 'attention'}>
                    {member.status === 'ACTIVE' ? 'Actif' : member.status}
                  </Badge>
                </Cell>
              </Row>
            ))}
          </Table>
        </Panel>

      </PageBody>
    </>
  )
}
