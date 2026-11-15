// Placement: frontend/src/pages/candidat/AtsDraft.tsx
import { useState } from 'react'
import { Badge, Button, Input, Note } from '../../components/ui'
import { proposeSummary, rewriteBullet, updateDraft, type AtsAnalysis, type DraftChange, type Rewrite } from '../../api/candidate'

const SECTIONS = [['experience', 'Expérience'], ['projects', 'Projets']] as const

function Editor({ proposal, initial, busy, onAccept, onReject }: { proposal?: Rewrite; initial: string; busy: boolean; onAccept: (text: string) => void; onReject?: () => void }) {
  const [text, setText] = useState(initial)
  return <div className="mt-2 space-y-2">
    {proposal?.source === 'rule' && <Note tone="attention">Aucune réécriture fiable n’a pu être produite. {proposal.suggestion}</Note>}
    <Input aria-label="Texte proposé" value={text} onChange={(event) => setText(event.target.value)} />
    {text.includes('[X') && <p className="text-[12px] text-slate">Remplacez [X] par votre vrai chiffre avant de générer le CV.</p>}
    <div className="flex gap-2">
      <Button size="sm" disabled={busy || !text.trim()} onClick={() => onAccept(text.trim())}>Accepter</Button>
      {onReject && <Button size="sm" variant="secondaire" disabled={busy} onClick={onReject}>Rejeter</Button>}
    </div>
  </div>
}

export default function AtsDraft({ analysis, onChange }: { analysis: AtsAnalysis; onChange: (analysis: AtsAnalysis) => void }) {
  const [proposals, setProposals] = useState<Record<string, Rewrite>>({})
  const [busy, setBusy] = useState('')
  const [error, setError] = useState('')
  const draft = analysis.cv_draft_json
  const entries = analysis.breakdown_json.structure?.entries ?? {}
  const missing = analysis.breakdown_json.skills.filter((skill) => skill.tier === 'core' && !skill.evidence).map((skill) => skill.name)

  async function run(key: string, task: () => Promise<void>) {
    setBusy(key); setError('')
    try { await task() } catch { setError('L’opération a échoué. Réessayez plus tard.') } finally { setBusy('') }
  }
  const propose = (key: string) => run(key, async () => {
    const proposal = key === 'summary' ? await proposeSummary(analysis.id) : await rewriteBullet(analysis.id, key)
    setProposals((current) => ({ ...current, [key]: proposal }))
  })
  const decide = (key: string, change: DraftChange) => run(key, async () => {
    onChange(await updateDraft(analysis.id, change))
    setProposals(({ [key]: _closed, ...rest }) => rest)
  })

  const bullets = SECTIONS.flatMap(([section, label]) => (entries[section] ?? []).flatMap((entry, e) => entry.bullets.map((bullet, b) => ({ key: `${section}.${e}.${b}`, label, entry, bullet }))))
  return <div className="space-y-5">
    <div>
      <h3 className="mb-1 text-sm font-semibold text-navy">Brouillon de CV</h3>
      <p className="text-[12px] text-slate">Les réécritures n’utilisent que les faits de votre puce. Rien n’est ajouté au brouillon sans votre accord, et votre profil n’est pas modifié.</p>
    </div>
    {error && <p role="alert" className="text-coral">{error}</p>}

    <section aria-label="Résumé professionnel" className="space-y-2">
      <h4 className="text-sm font-medium text-navy">Résumé professionnel</h4>
      {draft.summary && !proposals.summary && <p className="text-sm text-navy"><Badge tone="positif">Accepté</Badge> {draft.summary}</p>}
      {proposals.summary
        ? <Editor key={`summary-${proposals.summary.text}`} proposal={proposals.summary} initial={proposals.summary.text ?? draft.summary ?? ''} busy={busy === 'summary'} onAccept={(text) => void decide('summary', { summary: text })} />
        : <Button size="sm" variant="secondaire" disabled={!!busy} onClick={() => void propose('summary')}>{busy === 'summary' ? 'Rédaction…' : 'Proposer un résumé'}</Button>}
    </section>

    {missing.length > 0 && <section aria-label="Compétences manquantes" className="space-y-2">
      <h4 className="text-sm font-medium text-navy">Compétences clés manquantes</h4>
      {missing.map((skill) => {
        const answer = draft.confirmed_skills?.includes(skill) ? 'oui' : draft.declined_skills?.includes(skill) ? 'non' : ''
        return <div key={skill} className="flex flex-wrap items-center gap-2 text-sm text-navy">
          <span>Avez-vous de l’expérience avec {skill} ?</span>
          <Button size="sm" variant={answer === 'oui' ? 'primaire' : 'secondaire'} disabled={!!busy} onClick={() => void decide(skill, { skill, has_experience: true })}>Oui</Button>
          <Button size="sm" variant={answer === 'non' ? 'primaire' : 'secondaire'} disabled={!!busy} onClick={() => void decide(skill, { skill, has_experience: false })}>Non</Button>
        </div>
      })}
    </section>}

    <section aria-label="Puces" className="space-y-3">
      <h4 className="text-sm font-medium text-navy">Puces d’expérience et de projets</h4>
      {!bullets.length && <p className="text-sm text-slate">Aucune puce détectée dans ce CV.</p>}
      {bullets.map(({ key, label, entry, bullet }) => {
        const choice = draft.bullets?.[key]
        const proposal = proposals[key]
        return <div key={key} className="rounded-[6px] border border-line p-3">
          <p className="text-[12px] text-slate">{label}{entry.title ? ` — ${entry.title}` : ''}</p>
          <p className="text-sm text-navy">{bullet}</p>
          {choice && !proposal && <p className="mt-1 text-sm text-navy">{choice.decision === 'accept' ? <><Badge tone="positif">Acceptée</Badge> {choice.text}</> : <Badge tone="neutre">Rejetée : puce d’origine conservée</Badge>}</p>}
          {proposal
            ? <Editor key={`${key}-${proposal.text}`} proposal={proposal} initial={proposal.text ?? choice?.text ?? bullet} busy={busy === key} onAccept={(text) => void decide(key, { bullet: key, decision: 'accept', text })} onReject={() => void decide(key, { bullet: key, decision: 'reject' })} />
            : <Button className="mt-2" size="sm" variant="discret" disabled={!!busy} onClick={() => choice ? setProposals((current) => ({ ...current, [key]: { text: choice.text, source: 'model', suggestion: null } })) : void propose(key)}>{busy === key ? 'Réécriture…' : choice ? 'Modifier' : 'Proposer une réécriture'}</Button>}
        </div>
      })}
    </section>
  </div>
}
