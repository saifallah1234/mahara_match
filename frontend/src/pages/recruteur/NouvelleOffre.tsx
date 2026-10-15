import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Field, Input, Panel, Select, Textarea } from '../../components/ui'
import { useStore } from '../../state/store'
import { EDUCATION_LEVELS } from '../../data/referentials'
import { CONTRACT_LABEL, EXPERIENCE_LABEL, GOUVERNORATS, WORK_MODE_LABEL } from '../../lib/format'
import type {
  ContractType,
  ExperienceLevel,
  JobOffer,
  OfferSkill,
  SkillImportance,
  SkillLevel,
  WorkMode,
} from '../../lib/types'

export default function RecruteurNouvelleOffre() {
  const { session, organizations, skills, publishOffer, offers } = useStore()
  const navigate = useNavigate()

  const [title, setTitle] = useState('')
  const [description, setDescription] = useState('')
  const [organizationId, setOrganizationId] = useState(session?.user.organizationId ?? '')
  const [contractType, setContractType] = useState<ContractType>('CDI')
  const [workMode, setWorkMode] = useState<WorkMode>('ONSITE')
  const [governorate, setGovernorate] = useState('Ariana')
  const [city, setCity] = useState('')
  const [experienceLevel, setExperienceLevel] = useState<ExperienceLevel>('JUNIOR')
  const [educationLevelId, setEducationLevelId] = useState('')
  const [minSalary, setMinSalary] = useState('')
  const [maxSalary, setMaxSalary] = useState('')
  const [deadline, setDeadline] = useState('')
  const [easyApply, setEasyApply] = useState(true)
  const [chosen, setChosen] = useState<OfferSkill[]>([])
  const [skillToAdd, setSkillToAdd] = useState('')

  if (!session) return null

  const employers = organizations.filter((o) => o.type === 'COMPANY' || o.type === 'SUBSIDIARY')

  /* Contrôles exigés avant publication. */
  const problems: string[] = []
  if (!title.trim()) problems.push('Le titre du poste est obligatoire.')
  if (!description.trim()) problems.push('La description du poste est obligatoire.')
  if (!organizationId) problems.push('L’entité qui publie doit être sélectionnée.')
  if (chosen.length === 0) problems.push('Au moins une compétence doit être renseignée.')
  if (minSalary && maxSalary && Number(maxSalary) < Number(minSalary))
    problems.push('Le salaire maximum doit être supérieur ou égal au minimum.')

  function addSkill() {
    if (!skillToAdd || chosen.some((c) => c.skillId === skillToAdd)) return
    setChosen((list) => [...list, { skillId: skillToAdd, importance: 'OBLIGATOIRE', requiredLevel: 'INTERMEDIAIRE' }])
    setSkillToAdd('')
  }

  function build(status: 'DRAFT' | 'PUBLISHED'): JobOffer {
    const nextNumber = 300 + offers.length
    return {
      id: `of-${nextNumber}`,
      reference: `OF-${nextNumber}`,
      organizationId,
      createdBy: session!.user.id,
      title: title.trim(),
      description: description.trim(),
      contractType,
      workMode,
      governorate,
      city: city.trim() || governorate,
      experienceLevel,
      educationLevelId: educationLevelId || undefined,
      minSalary: minSalary ? Number(minSalary) : undefined,
      maxSalary: maxSalary ? Number(maxSalary) : undefined,
      applicationDeadline: deadline || undefined,
      status,
      publishedAt: status === 'PUBLISHED' ? new Date().toISOString() : undefined,
      easyApply,
      skills: chosen,
    }
  }

  function submit(status: 'DRAFT' | 'PUBLISHED') {
    publishOffer(build(status))
    navigate('/recruteur/offres')
  }

  const totalWeight = chosen.reduce((sum, c) => sum + (c.importance === 'OBLIGATOIRE' ? 2 : 1), 0)

  return (
    <>
      <PageHeader
        back={{ to: '/recruteur/offres', label: 'Mes offres' }}
        title="Publier une offre"
      />

      <PageBody className="space-y-6">
        <div className="grid gap-6 lg:grid-cols-[1fr_320px] lg:items-start">
          <div className="space-y-6">
            <Panel title="Le poste">
              <div className="grid gap-4 p-5 sm:grid-cols-2">
                <div className="sm:col-span-2">
                  <Field label="Intitulé du poste" required>
                    <Input value={title} onChange={(e) => setTitle(e.target.value)} placeholder="Développeur junior" />
                  </Field>
                </div>
                <div className="sm:col-span-2">
                  <Field label="Description" required hint="Missions, environnement de travail et attentes.">
                    <Textarea value={description} onChange={(e) => setDescription(e.target.value)} rows={6} />
                  </Field>
                </div>
                <Field label="Entité qui publie" required>
                  <Select value={organizationId} onChange={(e) => setOrganizationId(e.target.value)}>
                    <option value="">Choisir</option>
                    {employers.map((org) => (
                      <option key={org.id} value={org.id}>
                        {org.legalName}
                        {org.type === 'SUBSIDIARY' ? ' (filiale)' : ''}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Type de contrat" required>
                  <Select value={contractType} onChange={(e) => setContractType(e.target.value as ContractType)}>
                    {(Object.keys(CONTRACT_LABEL) as ContractType[]).map((type) => (
                      <option key={type} value={type}>
                        {CONTRACT_LABEL[type]}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Gouvernorat" required>
                  <Select value={governorate} onChange={(e) => setGovernorate(e.target.value)}>
                    {GOUVERNORATS.map((g) => (
                      <option key={g}>{g}</option>
                    ))}
                  </Select>
                </Field>
                <Field label="Ville">
                  <Input value={city} onChange={(e) => setCity(e.target.value)} />
                </Field>
                <Field label="Mode de travail">
                  <Select value={workMode} onChange={(e) => setWorkMode(e.target.value as WorkMode)}>
                    {(Object.keys(WORK_MODE_LABEL) as WorkMode[]).map((mode) => (
                      <option key={mode} value={mode}>
                        {WORK_MODE_LABEL[mode]}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Expérience attendue">
                  <Select value={experienceLevel} onChange={(e) => setExperienceLevel(e.target.value as ExperienceLevel)}>
                    {(Object.keys(EXPERIENCE_LABEL) as ExperienceLevel[]).map((level) => (
                      <option key={level} value={level}>
                        {EXPERIENCE_LABEL[level]}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Niveau d’études">
                  <Select value={educationLevelId} onChange={(e) => setEducationLevelId(e.target.value)}>
                    <option value="">Sans exigence</option>
                    {EDUCATION_LEVELS.map((level) => (
                      <option key={level.id} value={level.id}>
                        {level.name}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label="Salaire minimum (DT)" hint="Laisser vide si non communiqué.">
                  <Input type="number" value={minSalary} onChange={(e) => setMinSalary(e.target.value)} />
                </Field>
                <Field label="Salaire maximum (DT)">
                  <Input type="number" value={maxSalary} onChange={(e) => setMaxSalary(e.target.value)} />
                </Field>
                <Field label="Date limite de candidature">
                  <Input type="date" value={deadline} onChange={(e) => setDeadline(e.target.value)} />
                </Field>
                <Field label="Mode de candidature" hint="Hors plateforme, le suivi des candidatures et des entretiens n’est pas disponible.">
                  <Select value={easyApply ? 'oui' : 'non'} onChange={(e) => setEasyApply(e.target.value === 'oui')}>
                    <option value="oui">Sur la plateforme</option>
                    <option value="non">Sur le site de l’entreprise</option>
                  </Select>
                </Field>
              </div>
            </Panel>

            <Panel
              title="Compétences demandées"
              description="Une compétence obligatoire pèse 2 points, une compétence souhaitée 1 point."
            >
              <div className="flex gap-2 border-b border-line px-5 py-4">
                <Select value={skillToAdd} onChange={(e) => setSkillToAdd(e.target.value)}>
                  <option value="">Choisir une compétence du référentiel</option>
                  {skills
                    .filter((s) => !chosen.some((c) => c.skillId === s.id))
                    .map((skill) => (
                      <option key={skill.id} value={skill.id}>
                        {skill.canonicalName}
                      </option>
                    ))}
                </Select>
                <Button variant="secondaire" onClick={addSkill} disabled={!skillToAdd}>
                  Ajouter
                </Button>
              </div>

              {chosen.length === 0 ? (
                <p className="px-5 py-6 text-center text-[13px] text-slate">
                  Sans compétence renseignée, les candidats verront « score indisponible » et l’offre ne pourra pas être
                  publiée.
                </p>
              ) : (
                <ul className="divide-y divide-line/70">
                  {chosen.map((entry) => (
                    <li key={entry.skillId} className="flex flex-wrap items-center gap-3 px-5 py-3">
                      <span className="min-w-32 flex-1 text-[14px] font-medium text-navy">
                        {skills.find((s) => s.id === entry.skillId)?.canonicalName}
                      </span>
                      <Select
                        value={entry.importance}
                        onChange={(e) =>
                          setChosen((list) =>
                            list.map((c) =>
                              c.skillId === entry.skillId ? { ...c, importance: e.target.value as SkillImportance } : c,
                            ),
                          )
                        }
                        className="w-40"
                      >
                        <option value="OBLIGATOIRE">Obligatoire · 2</option>
                        <option value="SOUHAITEE">Souhaitée · 1</option>
                      </Select>
                      <Select
                        value={entry.requiredLevel}
                        onChange={(e) =>
                          setChosen((list) =>
                            list.map((c) =>
                              c.skillId === entry.skillId ? { ...c, requiredLevel: e.target.value as SkillLevel } : c,
                            ),
                          )
                        }
                        className="w-40"
                      >
                        <option value="DEBUTANT">Débutant</option>
                        <option value="INTERMEDIAIRE">Intermédiaire</option>
                        <option value="AVANCE">Avancé</option>
                        <option value="EXPERT">Expert</option>
                      </Select>
                      <Button
                        size="sm"
                        variant="discret"
                        onClick={() => setChosen((list) => list.filter((c) => c.skillId !== entry.skillId))}
                      >
                        Retirer
                      </Button>
                    </li>
                  ))}
                </ul>
              )}

              {chosen.length > 0 && (
                <p className="border-t border-line px-5 py-3 text-[13px] text-slate">
                  Total des points demandés : <span className="tnum font-medium text-navy">{totalWeight}</span>. Un
                  candidat qui couvre toutes les obligatoires sans les souhaitées obtiendra{' '}
                  <span className="tnum font-medium text-navy">
                    {Math.round((chosen.filter((c) => c.importance === 'OBLIGATOIRE').length * 2 * 100) / totalWeight)} %
                  </span>
                  .
                </p>
              )}
            </Panel>
          </div>

          <div className="space-y-4 lg:sticky lg:top-6">
            <Panel title="Avant publication">
              {problems.length === 0 ? (
                <div className="px-5 py-4">
                  <Badge tone="positif">Tous les champs obligatoires sont renseignés</Badge>
                </div>
              ) : (
                <ul className="space-y-2 px-5 py-4">
                  {problems.map((problem) => (
                    <li key={problem} className="flex gap-2.5 text-[13px] text-navy">
                      <span aria-hidden className="mt-[7px] h-1.5 w-1.5 shrink-0 rounded-full bg-coral" />
                      {problem}
                    </li>
                  ))}
                </ul>
              )}
              <div className="flex flex-col gap-2 border-t border-line px-5 py-3.5">
                <Button disabled={problems.length > 0} onClick={() => submit('PUBLISHED')}>
                  Publier l’offre
                </Button>
                <Button variant="secondaire" onClick={() => submit('DRAFT')} disabled={!title.trim()}>
                  Enregistrer en brouillon
                </Button>
              </div>
            </Panel>

          </div>
        </div>
      </PageBody>
    </>
  )
}
