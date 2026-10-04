import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Badge, Button, Field, Input, Meter, Panel, Select, Tabs, Textarea } from '../../components/ui'
import { useStore } from '../../state/store'
import { EDUCATION_LEVELS, LANGUAGES } from '../../data/referentials'
import {
  GOUVERNORATS,
  LANGUAGE_LEVEL_LABEL,
  SKILL_LEVEL_LABEL,
  WORK_MODE_LABEL,
  formatDate,
  formatMonthYear,
} from '../../lib/format'
import type { ProfileVisibility, Relocation, WorkMode } from '../../lib/types'

type Tab = 'identite' | 'parcours' | 'competences' | 'preferences'

const SOURCE_LABEL: Record<string, string> = {
  CV: 'extraite du CV',
  SAISIE: 'saisie manuellement',
  FORMATION: 'validée par une formation',
}

export default function CandidatProfil() {
  const { currentProfile, updateProfile, validateSkill, skills, userOf } = useStore()
  const [tab, setTab] = useState<Tab>('identite')
  if (!currentProfile) return null

  const user = userOf(currentProfile.userId)

  return (
    <>
      <PageHeader
        title="Mon profil"
      />

      <PageBody className="space-y-6">
        <Panel className="p-5">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="min-w-0 flex-1">
              <p className="text-[15px] font-semibold text-navy">
                {user?.firstName} {user?.lastName}
              </p>
              <p className="text-[13px] text-slate">{currentProfile.headline}</p>
              <div className="mt-2 flex flex-wrap gap-2">
                <Badge tone="neutre">
                  Visibilité :{' '}
                  {currentProfile.profileVisibility === 'PUBLIC'
                    ? 'publique'
                    : currentProfile.profileVisibility === 'RECRUITERS'
                      ? 'recruteurs'
                      : 'privée'}
                </Badge>
              </div>
            </div>
            <div className="w-full max-w-xs">
              <Meter value={currentProfile.completionScore} label="Complétude" />
            </div>
          </div>
        </Panel>

        <Tabs<Tab>
          active={tab}
          onChange={setTab}
          tabs={[
            { id: 'identite', label: 'Identité' },
            { id: 'parcours', label: 'Parcours', count: currentProfile.experiences.length + currentProfile.educations.length },
            { id: 'competences', label: 'Compétences', count: currentProfile.skills.length },
            { id: 'preferences', label: 'Préférences' },
          ]}
        />

        {tab === 'identite' && (
          <Panel title="Coordonnées et présentation">
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <Field label="Prénom" required>
                <Input defaultValue={user?.firstName} />
              </Field>
              <Field label="Nom" required>
                <Input defaultValue={user?.lastName} />
              </Field>
              <Field label="Adresse e-mail" required>
                <Input type="email" defaultValue={user?.email} />
              </Field>
              <Field label="Téléphone">
                <Input defaultValue={user?.phone} placeholder="+216 ..." />
              </Field>
              <Field label="Gouvernorat">
                <Select
                  defaultValue={currentProfile.governorate}
                  onChange={(e) => updateProfile({ governorate: e.target.value })}
                >
                  {GOUVERNORATS.map((g) => (
                    <option key={g}>{g}</option>
                  ))}
                </Select>
              </Field>
              <Field label="Ville">
                <Input defaultValue={currentProfile.city} />
              </Field>
              <div className="sm:col-span-2">
                <Field label="Titre d’accroche" hint="Une ligne qui annonce le poste visé, affichée en tête de votre profil.">
                  <Input defaultValue={currentProfile.headline} />
                </Field>
              </div>
              <div className="sm:col-span-2">
                <Field label="Présentation">
                  <Textarea defaultValue={currentProfile.summary} rows={4} />
                </Field>
              </div>
            </div>
            <div className="flex justify-end border-t border-line px-5 py-3.5">
              <Button onClick={() => updateProfile({})}>Enregistrer</Button>
            </div>
          </Panel>
        )}

        {tab === 'parcours' && (
          <div className="space-y-6">
            <Panel title="Expériences professionnelles" action={<Button size="sm" variant="secondaire">Ajouter</Button>}>
              <ul className="divide-y divide-line/70">
                {currentProfile.experiences.map((xp) => (
                  <li key={xp.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-[14px] font-medium text-navy">{xp.jobTitle}</p>
                      <p className="text-[12.5px] text-slate">
                        {formatMonthYear(xp.startDate)} – {formatMonthYear(xp.endDate)}
                      </p>
                    </div>
                    <p className="text-[13px] text-navy">{xp.organizationName}</p>
                    {xp.description && <p className="mt-1 text-[13px] leading-relaxed text-slate">{xp.description}</p>}
                  </li>
                ))}
              </ul>
            </Panel>

            <Panel title="Diplômes" action={<Button size="sm" variant="secondaire">Ajouter</Button>}>
              <ul className="divide-y divide-line/70">
                {currentProfile.educations.map((ed) => (
                  <li key={ed.id} className="px-5 py-4">
                    <div className="flex flex-wrap items-baseline justify-between gap-2">
                      <p className="text-[14px] font-medium text-navy">
                        {EDUCATION_LEVELS.find((l) => l.id === ed.educationLevelId)?.name} — {ed.fieldOfStudy}
                      </p>
                      <p className="tnum text-[12.5px] text-slate">
                        {ed.startYear} – {ed.endYear ?? 'en cours'}
                      </p>
                    </div>
                    <p className="text-[13px] text-navy">{ed.institution}</p>
                  </li>
                ))}
              </ul>
            </Panel>

            {currentProfile.certifications.length > 0 && (
              <Panel title="Certifications">
                <ul className="divide-y divide-line/70">
                  {currentProfile.certifications.map((cert) => (
                    <li key={cert.id} className="px-5 py-4">
                      <p className="text-[14px] font-medium text-navy">{cert.name}</p>
                      <p className="text-[13px] text-navy">{cert.certificationOrganization}</p>
                      <p className="mt-0.5 text-[12.5px] text-slate">
                        Obtenue le {formatDate(cert.issueDate)}
                        {cert.credentialId && ` · identifiant ${cert.credentialId}`}
                      </p>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}

            {currentProfile.projects.length > 0 && (
              <Panel title="Projets">
                <ul className="divide-y divide-line/70">
                  {currentProfile.projects.map((project) => (
                    <li key={project.id} className="px-5 py-4">
                      <div className="flex flex-wrap items-baseline justify-between gap-2">
                        <p className="text-[14px] font-medium text-navy">{project.name}</p>
                        <p className="text-[12.5px] text-slate">
                          {formatMonthYear(project.startDate)} – {formatMonthYear(project.endDate)}
                        </p>
                      </div>
                      <p className="text-[13px] text-slate">{project.role}</p>
                      <p className="mt-1 text-[13px] leading-relaxed text-navy">{project.description}</p>
                      <div className="mt-2 flex flex-wrap gap-1.5">
                        {project.technologies.map((tech) => (
                          <Badge key={tech} tone="teal">
                            {tech}
                          </Badge>
                        ))}
                      </div>
                    </li>
                  ))}
                </ul>
              </Panel>
            )}
          </div>
        )}

        {tab === 'competences' && (
          <div className="space-y-6">
            <Panel title="Mes compétences" action={<Button size="sm" variant="secondaire">Ajouter</Button>}>
              <ul className="divide-y divide-line/70">
                {currentProfile.skills.map((candidateSkill) => {
                  const skill = skills.find((s) => s.id === candidateSkill.skillId)
                  return (
                    <li key={candidateSkill.skillId} className="flex flex-wrap items-center justify-between gap-3 px-5 py-3.5">
                      <div className="min-w-0">
                        <p className="text-[14px] font-medium text-navy">{skill?.canonicalName}</p>
                        <p className="text-[12.5px] text-slate">
                          {SKILL_LEVEL_LABEL[candidateSkill.level]} · {candidateSkill.yearsExperience} an
                          {candidateSkill.yearsExperience > 1 ? 's' : ''} · {SOURCE_LABEL[candidateSkill.source]}
                        </p>
                      </div>
                      {candidateSkill.validated ? (
                        <Badge tone="positif">Confirmée</Badge>
                      ) : (
                        <div className="flex items-center gap-2">
                          <Badge tone="attention">Non confirmée</Badge>
                          <Button size="sm" variant="secondaire" onClick={() => validateSkill(candidateSkill.skillId)}>
                            Confirmer
                          </Button>
                        </div>
                      )}
                    </li>
                  )
                })}
              </ul>
            </Panel>

            <Panel title="Langues">
              <ul className="divide-y divide-line/70">
                {currentProfile.languages.map((candidateLanguage) => (
                  <li
                    key={candidateLanguage.languageId}
                    className="flex items-center justify-between px-5 py-3.5 text-[14px]"
                  >
                    <span className="font-medium text-navy">
                      {LANGUAGES.find((l) => l.id === candidateLanguage.languageId)?.name}
                    </span>
                    <span className="text-slate">{LANGUAGE_LEVEL_LABEL[candidateLanguage.level]}</span>
                  </li>
                ))}
              </ul>
            </Panel>
          </div>
        )}

        {tab === 'preferences' && (
          <Panel title="Mes préférences">
            <div className="grid gap-4 p-5 sm:grid-cols-2">
              <Field label="Poste souhaité">
                <Input defaultValue={currentProfile.desiredJobTitle} />
              </Field>
              <Field label="Disponible à partir du">
                <Input type="date" defaultValue={currentProfile.availabilityDate} />
              </Field>
              <Field label="Mode de travail souhaité">
                <Select
                  defaultValue={currentProfile.preferredWorkMode}
                  onChange={(e) => updateProfile({ preferredWorkMode: e.target.value as WorkMode })}
                >
                  {(Object.keys(WORK_MODE_LABEL) as WorkMode[]).map((mode) => (
                    <option key={mode} value={mode}>
                      {WORK_MODE_LABEL[mode]}
                    </option>
                  ))}
                </Select>
              </Field>
              <Field label="Distance acceptée" hint="Rayon autour de votre ville.">
                <Select
                  defaultValue={String(currentProfile.maxDistanceKm)}
                  onChange={(e) => updateProfile({ maxDistanceKm: Number(e.target.value) })}
                >
                  <option value="20">Jusqu’à 20 km</option>
                  <option value="50">Jusqu’à 50 km</option>
                  <option value="100">Jusqu’à 100 km</option>
                  <option value="1000">Toute la Tunisie</option>
                </Select>
              </Field>
              <Field label="Mobilité">
                <Select
                  defaultValue={currentProfile.relocation}
                  onChange={(e) => updateProfile({ relocation: e.target.value as Relocation })}
                >
                  <option value="OPEN_TO_RELOCATE">Prête à déménager</option>
                  <option value="CANNOT_RELOCATE">Ne peut pas déménager</option>
                </Select>
              </Field>
              <Field label="Visibilité du profil" hint="Détermine qui peut consulter vos informations avant que vous postuliez.">
                <Select
                  defaultValue={currentProfile.profileVisibility}
                  onChange={(e) => updateProfile({ profileVisibility: e.target.value as ProfileVisibility })}
                >
                  <option value="PRIVATE">Privé — visible par moi seule</option>
                  <option value="RECRUITERS">Recruteurs — visible par les entreprises vérifiées</option>
                  <option value="PUBLIC">Public — visible par tous</option>
                </Select>
              </Field>
            </div>
            <div className="flex justify-end border-t border-line px-5 py-3.5">
              <Button onClick={() => updateProfile({})}>Enregistrer</Button>
            </div>
          </Panel>
        )}
      </PageBody>
    </>
  )
}
