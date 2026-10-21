// Placement: frontend/src/pages/recruteur/Candidats.tsx
import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { EmptyState, Field, Input, Note, Panel, Select } from '../../components/ui'
import { useAuth } from '../../state/auth'
import { useRecruiter } from '../../state/recruiter'
import { listCandidates, listEducationLevels, type CandidateCard, type EducationLevel } from '../../api/recruiter'
import { GOUVERNORATS, WORK_MODE_LABEL } from '../../lib/format'
import { RELOCATION_LABEL, UNVERIFIED_MESSAGE } from '../../lib/recruiterCandidates'

const EMPTY = { skill: '', education_level: '', governorate: '', work_mode: '', relocation: '', search: '' }

export default function RecruteurCandidats() {
  const { workspace } = useAuth()
  const { skills } = useRecruiter()
  const verified = workspace?.organization?.verification_status === 'VERIFIED'
  const [filters, setFilters] = useState(EMPTY)
  const [levels, setLevels] = useState<EducationLevel[]>([])
  const [cards, setCards] = useState<CandidateCard[] | null>(null)
  const [loadError, setLoadError] = useState<string | null>(null)
  const query = new URLSearchParams(Object.entries(filters).filter(([, value]) => value)).toString()
  const set = (key: keyof typeof EMPTY) => (e: { target: { value: string } }) => setFilters({ ...filters, [key]: e.target.value })
  const skillName = (id: string) => skills.find((s) => s.id === id)?.canonical_name

  useEffect(() => {
    if (!verified) return
    let live = true
    listEducationLevels().then((rows) => { if (live) setLevels(rows) }).catch(() => {})
    return () => { live = false }
  }, [verified])

  useEffect(() => {
    if (!verified) return
    let live = true
    setCards(null)
    listCandidates(query ? `?${query}` : '')
      .then((rows) => { if (live) { setCards(rows); setLoadError(null) } })
      .catch((e: unknown) => { if (live) setLoadError(e instanceof Error ? e.message : 'Recherche impossible.') })
    return () => { live = false }
  }, [query, verified])

  return (
    <>
      <PageHeader title="Candidats" />
      <PageBody className="space-y-6">
        {!verified ? (
          <Note tone="attention">{UNVERIFIED_MESSAGE}</Note>
        ) : (
          <>
            <Panel title="Filtres">
              <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-3">
                <Field label="Recherche"><Input value={filters.search} onChange={set('search')} placeholder="Titre, expérience…" /></Field>
                <Field label="Compétence">
                  <Select value={filters.skill} onChange={set('skill')}>
                    <option value="">Toutes</option>
                    {skills.map((s) => <option key={s.id} value={s.id}>{s.canonical_name}</option>)}
                  </Select>
                </Field>
                <Field label="Niveau de formation">
                  <Select value={filters.education_level} onChange={set('education_level')}>
                    <option value="">Tous</option>
                    {levels.map((l) => <option key={l.id} value={l.id}>{l.name}</option>)}
                  </Select>
                </Field>
                <Field label="Gouvernorat">
                  <Select value={filters.governorate} onChange={set('governorate')}>
                    <option value="">Tous</option>
                    {GOUVERNORATS.map((g) => <option key={g}>{g}</option>)}
                  </Select>
                </Field>
                <Field label="Mode de travail">
                  <Select value={filters.work_mode} onChange={set('work_mode')}>
                    <option value="">Tous</option>
                    {Object.entries(WORK_MODE_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </Select>
                </Field>
                <Field label="Mobilité">
                  <Select value={filters.relocation} onChange={set('relocation')}>
                    <option value="">Toutes</option>
                    {Object.entries(RELOCATION_LABEL).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                  </Select>
                </Field>
              </div>
            </Panel>

            {loadError && <p role="alert" className="text-coral">{loadError}</p>}
            <Panel title={cards ? `Profils (${cards.length})` : 'Profils'}>
              {!cards ? (
                <p className="p-5 text-slate">Chargement…</p>
              ) : cards.length === 0 ? (
                <EmptyState title="Aucun profil ne correspond à ces critères." />
              ) : (
                <ul className="divide-y divide-line/70">
                  {cards.map((c) => (
                    <li key={c.id}>
                      <Link to={`/recruteur/candidats/${c.id}`} className="block px-5 py-4 hover:bg-mist/50">
                        <p className="font-medium text-navy">{c.headline || 'Candidat'}</p>
                        <p className="text-[12.5px] text-slate">
                          {c.governorate || 'Gouvernorat non renseigné'}
                          {c.skills.length > 0 && ` · ${c.skills.slice(0, 4).map((s) => skillName(s.skill) ?? 'Compétence').join(', ')}`}
                        </p>
                      </Link>
                    </li>
                  ))}
                </ul>
              )}
            </Panel>
          </>
        )}
      </PageBody>
    </>
  )
}
