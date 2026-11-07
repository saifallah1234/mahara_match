import { useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { Input, Panel } from '../../components/ui'
import { useSkillCatalog } from '../../state/adminData'
import { skillLabel } from '../../lib/format'

export default function AdminReferentiels() {
  const { data: skills, loading, error } = useSkillCatalog()
  const [q, setQ] = useState('')
  const shown = skills.filter((s) => s.canonical_name.toLowerCase().includes(q.toLowerCase()))
  const groups = [...new Set(shown.map((s) => s.category || 'Sans catégorie'))].sort()
  return (
    <>
      <PageHeader title="Référentiel des compétences" action={<Input placeholder="Rechercher…" value={q} onChange={(e) => setQ(e.target.value)} className="min-w-56" />} />
      <PageBody className="space-y-4">
        {error && <p role="alert" className="text-coral">{error}</p>}
        <p className="text-[13px] text-slate">{skills.length} compétences. Le référentiel est en lecture seule : l’ajout et les alias ne sont pas encore exposés par l’API.</p>
        {loading ? <p className="text-slate">Chargement…</p> : groups.map((g) => (
          <Panel key={g} title={g}>
            <div className="flex flex-wrap gap-2 p-5">
              {shown.filter((s) => (s.category || 'Sans catégorie') === g).map((s) => (
                <span key={s.id} className="rounded-full border border-line bg-white px-3 py-1 text-[13px] text-navy">{skillLabel(s.canonical_name)}</span>
              ))}
            </div>
          </Panel>
        ))}
      </PageBody>
    </>
  )
}