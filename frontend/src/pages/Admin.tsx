import { useState } from 'react'
import { PageBody, PageHeader } from './../components/layout'
import { Badge, Button, Cell, EmptyState, Input, Panel, Row, Select, StatTile, Table, Tabs } from './../components/ui'
import { useStore } from '../state/store'
import { PERMISSIONS, ROLE_PERMISSIONS } from '../data/referentials'
import { ROLE_LABEL, formatDate, formatDateTime, formatPlace } from '../lib/format'
import type { RoleCode, UserStatus } from '../lib/types'

/* ------------------------------------------------------------------ */

export function AdminDashboard() {
  const { users, organizations, offers, applications, batches, auditLogs } = useStore()

  const pendingOrgs = organizations.filter((o) => o.verificationStatus === 'PENDING')
  const pendingUsers = users.filter((u) => u.status === 'PENDING')
  const lastBatch = batches.find((b) => b.status === 'COMPLETED')

  return (
    <>
      <PageHeader
        title="Administration"
        description="Comptes, organisations, référentiels et traçabilité de la plateforme."
      />

      <PageBody className="space-y-6">
        <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
          <StatTile value={users.length} label="Comptes" note={`${pendingUsers.length} en attente d’activation`} />
          <StatTile value={organizations.length} label="Organisations" note={`${pendingOrgs.length} à vérifier`} tone="coral" />
          <StatTile value={offers.filter((o) => o.status === 'PUBLISHED').length} label="Offres publiées" tone="teal" />
          <StatTile value={applications.length} label="Candidatures" tone="leaf" />
        </div>

        <div className="grid gap-6 lg:grid-cols-2">
          <Panel title="À traiter">
            <ul className="divide-y divide-line/70">
              {pendingOrgs.map((org) => (
                <li key={org.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="text-[13.5px] font-medium text-navy">{org.legalName}</p>
                    <p className="text-[12.5px] text-slate">
                      Organisation à vérifier · créée le {formatDate(org.createdAt)}
                    </p>
                  </div>
                  <Badge tone="attention">En attente</Badge>
                </li>
              ))}
              {pendingUsers.map((user) => (
                <li key={user.id} className="flex items-center justify-between gap-3 px-5 py-3.5">
                  <div className="min-w-0">
                    <p className="text-[13.5px] font-medium text-navy">
                      {user.firstName} {user.lastName}
                    </p>
                    <p className="text-[12.5px] text-slate">Compte non activé · {user.email}</p>
                  </div>
                  <Badge tone="attention">En attente</Badge>
                </li>
              ))}
              {pendingOrgs.length === 0 && pendingUsers.length === 0 && (
                <li>
                  <EmptyState title="Rien en attente" />
                </li>
              )}
            </ul>
          </Panel>

          <Panel title="Dernier lot d’import">
            {lastBatch ? (
              <div className="px-5 py-4">
                <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
                  {[
                    ['Ajoutées', lastBatch.addedCount, 'text-leaf'],
                    ['Modifiées', lastBatch.updatedCount, 'text-teal'],
                    ['Inchangées', lastBatch.unchangedCount, 'text-slate'],
                    ['Rejetées', lastBatch.rejectedCount, 'text-coral'],
                  ].map(([label, value, color]) => (
                    <div key={label as string}>
                      <p className={`tnum text-xl font-semibold ${color}`}>{value as number}</p>
                      <p className="text-[12.5px] text-slate">{label as string}</p>
                    </div>
                  ))}
                </div>
                <p className="mt-3 text-[12.5px] text-slate">
                  Terminé le {formatDateTime(lastBatch.completedAt)} · empreinte {lastBatch.checksum}
                </p>
              </div>
            ) : (
              <EmptyState title="Aucun lot terminé" />
            )}
          </Panel>
        </div>

        <Panel title="Dernières opérations sensibles">
          <ul className="divide-y divide-line/70">
            {auditLogs.slice(0, 6).map((log) => (
              <li key={log.id} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3">
                <div className="min-w-0">
                  <p className="text-[13.5px] text-navy">{log.action}</p>
                  <p className="text-[12.5px] text-slate">
                    {log.actorLabel} · {log.entityType} {log.entityId}
                  </p>
                </div>
                <div className="flex items-center gap-3">
                  <Badge tone={log.actorKind === 'AGENT_IA' ? 'teal' : log.actorKind === 'SYSTEME' ? 'neutre' : 'encours'}>
                    {log.actorKind === 'AGENT_IA' ? 'Agent IA' : log.actorKind === 'SYSTEME' ? 'Système' : 'Utilisateur'}
                  </Badge>
                  <span className="text-[12.5px] text-slate">{formatDateTime(log.createdAt)}</span>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

const STATUS_TONE: Record<UserStatus, 'positif' | 'attention' | 'negatif' | 'neutre'> = {
  ACTIVE: 'positif',
  PENDING: 'attention',
  SUSPENDED: 'negatif',
  DISABLED: 'neutre',
}

const STATUS_TEXT: Record<UserStatus, string> = {
  ACTIVE: 'Actif',
  PENDING: 'En attente',
  SUSPENDED: 'Suspendu',
  DISABLED: 'Désactivé',
}

export function AdminComptes() {
  const { users, organizationOf, setUserStatus } = useStore()
  const [tab, setTab] = useState<'comptes' | 'matrice'>('comptes')
  const [roleFilter, setRoleFilter] = useState('')

  const shown = users.filter((u) => !roleFilter || u.roles.includes(roleFilter as RoleCode))

  return (
    <>
      <PageHeader
        title="Comptes et rôles"
        action={
          <Select value={roleFilter} onChange={(e) => setRoleFilter(e.target.value)} className="min-w-56">
            <option value="">Tous les rôles</option>
            {(Object.keys(ROLE_LABEL) as RoleCode[]).map((role) => (
              <option key={role} value={role}>
                {ROLE_LABEL[role]}
              </option>
            ))}
          </Select>
        }
      />

      <PageBody className="space-y-5">
        <Tabs<'comptes' | 'matrice'>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'comptes', label: 'Comptes', count: users.length },
            { id: 'matrice', label: 'Matrice des permissions' },
          ]}
        />

        {tab === 'comptes' && (
          <Panel>
            <Table head={['Utilisateur', 'Rôles', 'Organisation', 'Dernière connexion', 'Statut', '']}>
              {shown.map((user) => (
                <Row key={user.id}>
                  <Cell>
                    <p className="font-medium text-navy">
                      {user.firstName} {user.lastName}
                    </p>
                    <p className="text-[12.5px] text-slate">{user.email}</p>
                  </Cell>
                  <Cell>
                    <div className="flex flex-wrap gap-1.5">
                      {user.roles.map((role) => (
                        <Badge key={role} tone="teal">
                          {ROLE_LABEL[role]}
                        </Badge>
                      ))}
                    </div>
                  </Cell>
                  <Cell className="text-[13px] text-slate">
                    {user.roleAssignments?.filter((entry) => entry.organizationId).map((entry) =>
                      organizationOf(entry.organizationId)?.legalName ?? entry.organizationId
                    ).join(', ') || 'Portée plateforme'}
                  </Cell>
                  <Cell className="text-[13px] text-slate">{formatDate(user.lastLoginAt)}</Cell>
                  <Cell>
                    <Badge tone={STATUS_TONE[user.status]}>{STATUS_TEXT[user.status]}</Badge>
                  </Cell>
                  <Cell className="text-right">
                    {user.status === 'ACTIVE' ? (
                      <Button size="sm" variant="discret" onClick={() => setUserStatus(user.id, 'SUSPENDED')}>
                        Suspendre
                      </Button>
                    ) : (
                      <Button size="sm" variant="discret" onClick={() => setUserStatus(user.id, 'ACTIVE')}>
                        Activer
                      </Button>
                    )}
                  </Cell>
                </Row>
              ))}
            </Table>
          </Panel>
        )}

        {tab === 'matrice' && (
          <>
            <Panel title="Matrice des rôles et permissions">
              <div className="overflow-x-auto">
                <table className="w-full border-collapse text-sm">
                  <thead>
                    <tr className="border-b border-line">
                      <th className="px-5 py-2.5 text-left text-[12px] font-semibold text-slate">Permission</th>
                      {(Object.keys(ROLE_LABEL) as RoleCode[]).map((role) => (
                        <th key={role} className="px-3 py-2.5 text-center text-[12px] font-semibold text-slate">
                          {ROLE_LABEL[role].split(' ')[0]}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {PERMISSIONS.map((permission) => (
                      <tr key={permission.code} className="border-b border-line/70 last:border-0">
                        <td className="px-5 py-2.5">
                          <p className="text-[13.5px] text-navy">
                            {permission.resource} — {permission.action}
                          </p>
                          <p className="text-[12px] text-slate">{permission.code}</p>
                        </td>
                        {(Object.keys(ROLE_LABEL) as RoleCode[]).map((role) => {
                          const granted = ROLE_PERMISSIONS[role].includes(permission.code)
                          return (
                            <td key={role} className="px-3 py-2.5 text-center">
                              {granted ? (
                                <span
                                  aria-label="Accordée"
                                  className="inline-flex h-5 w-5 items-center justify-center rounded-full bg-leaf/12 text-leaf"
                                >
                                  <svg width="11" height="11" viewBox="0 0 16 16" fill="none" aria-hidden>
                                    <path d="M3.5 8.5l3 3 6-7" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
                                  </svg>
                                </span>
                              ) : (
                                <span aria-label="Non accordée" className="text-slate/40">
                                  —
                                </span>
                              )}
                            </td>
                          )
                        })}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </Panel>
          </>
        )}
      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function AdminOrganisations() {
  const { organizations, verifyOrganization, offers, users } = useStore()

  return (
    <>
      <PageHeader
        title="Organisations"
      />

      <PageBody>
        <Panel>
          <Table head={['Organisation', 'Type', 'Matricule fiscal', 'Membres', 'Offres', 'Vérification', '']}>
            {organizations.map((org) => {
              const parent = organizations.find((o) => o.id === org.parentId)
              return (
                <Row key={org.id}>
                  <Cell>
                    <p className="font-medium text-navy">{org.legalName}</p>
                    <p className="text-[12.5px] text-slate">
                      {formatPlace(org.city, org.governorate)}
                      {parent && ` · filiale de ${parent.legalName}`}
                    </p>
                  </Cell>
                  <Cell className="text-[13px] text-slate">
                    {org.type === 'COMPANY'
                      ? 'Entreprise'
                      : org.type === 'SUBSIDIARY'
                        ? 'Filiale'
                        : org.type === 'TRAINING_PROVIDER'
                          ? 'Organisme de formation'
                          : 'Ministère'}
                  </Cell>
                  <Cell className="tnum text-[13px] text-slate">{org.matriculeFiscal ?? '—'}</Cell>
                  <Cell className="tnum text-[13px] text-navy">
                    {users.filter((u) => u.organizationId === org.id).length}
                  </Cell>
                  <Cell className="tnum text-[13px] text-navy">
                    {offers.filter((o) => o.organizationId === org.id).length}
                  </Cell>
                  <Cell>
                    <Badge
                      tone={
                        org.verificationStatus === 'VERIFIED'
                          ? 'positif'
                          : org.verificationStatus === 'PENDING'
                            ? 'attention'
                            : 'negatif'
                      }
                    >
                      {org.verificationStatus === 'VERIFIED'
                        ? 'Vérifiée'
                        : org.verificationStatus === 'PENDING'
                          ? 'En attente'
                          : 'Rejetée'}
                    </Badge>
                  </Cell>
                  <Cell className="text-right">
                    {org.verificationStatus === 'PENDING' && (
                      <div className="flex justify-end gap-1.5">
                        <Button size="sm" variant="secondaire" onClick={() => verifyOrganization(org.id, 'VERIFIED')}>
                          Vérifier
                        </Button>
                        <Button size="sm" variant="danger" onClick={() => verifyOrganization(org.id, 'REJECTED')}>
                          Rejeter
                        </Button>
                      </div>
                    )}
                  </Cell>
                </Row>
              )
            })}
          </Table>
        </Panel>
      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function AdminReferentiels() {
  const { skills, addSkillAlias, offers, programs } = useStore()
  const [target, setTarget] = useState('')
  const [alias, setAlias] = useState('')

  return (
    <>
      <PageHeader
        title="Référentiel des compétences"
      />

      <PageBody className="space-y-6">
        <Panel title="Ajouter un alias">
          <div className="flex flex-wrap gap-3 p-5">
            <Select value={target} onChange={(e) => setTarget(e.target.value)} className="min-w-56 flex-1">
              <option value="">Compétence de destination</option>
              {skills.map((skill) => (
                <option key={skill.id} value={skill.id}>
                  {skill.canonicalName}
                </option>
              ))}
            </Select>
            <Input
              value={alias}
              onChange={(e) => setAlias(e.target.value)}
              placeholder="Libellé à normaliser, ex. « dev web »"
              className="min-w-56 flex-1"
            />
            <Button
              disabled={!target || !alias.trim()}
              onClick={() => {
                addSkillAlias(target, alias.trim())
                setAlias('')
              }}
            >
              Ajouter
            </Button>
          </div>
        </Panel>

        <Panel title="Compétences normalisées" description={`${skills.length} entrées au référentiel`}>
          <Table head={['Compétence', 'Catégorie', 'Alias', 'Offres', 'Formations']}>
            {skills.map((skill) => (
              <Row key={skill.id}>
                <Cell>
                  <p className="font-medium text-navy">{skill.canonicalName}</p>
                  {skill.description && <p className="text-[12.5px] text-slate">{skill.description}</p>}
                </Cell>
                <Cell className="text-[13px] text-slate">{skill.category.toLowerCase()}</Cell>
                <Cell>
                  <div className="flex flex-wrap gap-1.5">
                    {skill.aliases.length === 0 ? (
                      <span className="text-[12.5px] text-slate">—</span>
                    ) : (
                      skill.aliases.map((a) => (
                        <Badge key={a} tone="neutre">
                          {a}
                        </Badge>
                      ))
                    )}
                  </div>
                </Cell>
                <Cell className="tnum text-[13px] text-navy">
                  {offers.filter((o) => o.skills.some((os) => os.skillId === skill.id)).length}
                </Cell>
                <Cell className="tnum text-[13px] text-navy">
                  {programs.filter((p) => p.skillIds.includes(skill.id)).length}
                </Cell>
              </Row>
            ))}
          </Table>
        </Panel>
      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function AdminImports() {
  const { batches, rows, sources } = useStore()
  const [selected, setSelected] = useState<string | null>(batches[1]?.id ?? null)

  const batchRows = rows.filter((r) => r.batchId === selected)

  return (
    <>
      <PageHeader
        title="Imports d’offres"
      />

      <PageBody className="space-y-6">
        <Panel title="Sources autorisées">
          <Table head={['Source', 'Type', 'Adresse', 'Autorisation']}>
            {sources.map((source) => (
              <Row key={source.id}>
                <Cell className="font-medium text-navy">{source.name}</Cell>
                <Cell className="text-[13px] text-slate">{source.type}</Cell>
                <Cell className="text-[13px] text-slate">{source.baseUrl ?? '—'}</Cell>
                <Cell>
                  <Badge tone={source.isAuthorized ? 'positif' : 'negatif'}>
                    {source.isAuthorized ? 'Autorisée' : 'Non autorisée'}
                  </Badge>
                </Cell>
              </Row>
            ))}
          </Table>
        </Panel>

        <Panel title="Lots d’import">
          <Table head={['Lot', 'Source', 'Ajoutées', 'Modifiées', 'Inchangées', 'Rejetées', 'Statut', '']}>
            {batches.map((batch) => (
              <Row key={batch.id}>
                <Cell>
                  <p className="font-medium text-navy">{batch.id}</p>
                  <p className="text-[12.5px] text-slate">empreinte {batch.checksum}</p>
                </Cell>
                <Cell className="text-[13px] text-slate">{sources.find((s) => s.id === batch.sourceId)?.name}</Cell>
                <Cell className="tnum text-[13px] text-leaf">{batch.addedCount}</Cell>
                <Cell className="tnum text-[13px] text-teal">{batch.updatedCount}</Cell>
                <Cell className="tnum text-[13px] text-slate">{batch.unchangedCount}</Cell>
                <Cell className="tnum text-[13px] text-coral">{batch.rejectedCount}</Cell>
                <Cell>
                  <Badge tone={batch.status === 'COMPLETED' ? 'positif' : batch.status === 'RUNNING' ? 'encours' : 'negatif'}>
                    {batch.status === 'COMPLETED' ? 'Terminé' : batch.status === 'RUNNING' ? 'En cours' : 'Échec'}
                  </Badge>
                </Cell>
                <Cell className="text-right">
                  <Button size="sm" variant="discret" onClick={() => setSelected(batch.id)}>
                    Détail
                  </Button>
                </Cell>
              </Row>
            ))}
          </Table>
        </Panel>

        <Panel
          title="Lignes du lot"
          description={selected ? `Traçabilité ligne par ligne du lot ${selected}` : 'Choisissez un lot'}
        >
          {batchRows.length === 0 ? (
            <EmptyState title="Aucune ligne détaillée pour ce lot" />
          ) : (
            <Table head={['Ligne', 'Identifiant externe', 'Résultat', 'Motif']}>
              {batchRows.map((row) => (
                <Row key={row.id}>
                  <Cell className="tnum text-[13px] text-slate">{row.rowNumber}</Cell>
                  <Cell className="text-[13px] text-navy">{row.externalId ?? '—'}</Cell>
                  <Cell>
                    <Badge
                      tone={
                        row.status === 'ADDED'
                          ? 'positif'
                          : row.status === 'UPDATED'
                            ? 'teal'
                            : row.status === 'REJECTED'
                              ? 'negatif'
                              : 'neutre'
                      }
                    >
                      {row.status === 'ADDED'
                        ? 'Ajoutée'
                        : row.status === 'UPDATED'
                          ? 'Modifiée'
                          : row.status === 'REJECTED'
                            ? 'Rejetée'
                            : 'Inchangée'}
                    </Badge>
                  </Cell>
                  <Cell className="text-[13px] text-slate">
                    {row.errorMessage ? (
                      <>
                        <span className="font-medium text-navy">{row.errorCode}</span> — {row.errorMessage}
                      </>
                    ) : (
                      '—'
                    )}
                  </Cell>
                </Row>
              ))}
            </Table>
          )}
        </Panel>

      </PageBody>
    </>
  )
}

/* ------------------------------------------------------------------ */

export function AdminAudit() {
  const { auditLogs } = useStore()
  const [kind, setKind] = useState('')

  const shown = auditLogs.filter((log) => !kind || log.actorKind === kind)

  return (
    <>
      <PageHeader
        title="Journal d’audit"
        action={
          <Select value={kind} onChange={(e) => setKind(e.target.value)} className="min-w-48">
            <option value="">Tous les auteurs</option>
            <option value="UTILISATEUR">Utilisateurs</option>
            <option value="AGENT_IA">Agent conversationnel</option>
            <option value="SYSTEME">Système</option>
          </Select>
        }
      />

      <PageBody>
        <Panel>
          <Table head={['Horodatage', 'Auteur', 'Action', 'Entité', 'Adresse IP']}>
            {shown.map((log) => (
              <Row key={log.id}>
                <Cell className="whitespace-nowrap text-[13px] text-slate">{formatDateTime(log.createdAt)}</Cell>
                <Cell>
                  <p className="text-[13px] font-medium text-navy">{log.actorLabel}</p>
                  <Badge tone={log.actorKind === 'AGENT_IA' ? 'teal' : log.actorKind === 'SYSTEME' ? 'neutre' : 'encours'}>
                    {log.actorKind === 'AGENT_IA' ? 'Agent IA' : log.actorKind === 'SYSTEME' ? 'Système' : 'Utilisateur'}
                  </Badge>
                </Cell>
                <Cell className="text-[13px] text-navy">{log.action}</Cell>
                <Cell className="text-[13px] text-slate">
                  {log.entityType} <span className="text-slate/70">{log.entityId}</span>
                </Cell>
                <Cell className="tnum text-[13px] text-slate">{log.ipAddress ?? '—'}</Cell>
              </Row>
            ))}
          </Table>
        </Panel>
      </PageBody>
    </>
  )
}
