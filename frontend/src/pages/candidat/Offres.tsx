import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { Button, EmptyState, Field, Input, Loading, Note, Panel, Select } from '../../components/ui'
import { publishedOffers, type Offer } from '../../api/candidate'
import { filterCandidateOffers } from '../../lib/candidateOffers'
import { useCandidate } from '../../state/candidate'
import { CONTRACT_OPTIONS, GOUVERNORATS, WORK_MODE_LABEL, contractLabel, formatDate, labelFor } from '../../lib/format'
import { MatchBadge, useAutoMatches } from '../../components/insights'

export default function CandidatOffres() {
  const { offers: initial, records, matches, loading: profileLoading, calculating, scoresStale, calculateMatches } = useCandidate()
  useAutoMatches()
  const [search, setSearch] = useState('')
  const [governorate, setGovernorate] = useState('')
  const [contract, setContract] = useState('')
  const [mode, setMode] = useState('')
  const [offers, setOffers] = useState<Offer[]>(initial)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => {
    let live = true
    const timer = setTimeout(() => {
      setLoading(true); setError('')
      void publishedOffers(search, governorate).then((data) => { if (live) setOffers(data) })
        .catch((failure) => { if (live) setError(failure instanceof Error ? failure.message : 'Recherche impossible.') })
        .finally(() => { if (live) setLoading(false) })
    }, 250)
    return () => { live = false; clearTimeout(timer) }
  }, [search, governorate])
  const results = filterCandidateOffers(offers, contract, mode)
  return <>
    <PageHeader title="Offres d’emploi" action={records.skills.length > 0 && (scoresStale || !matches.length) && (
      <Button variant="secondaire" disabled={calculating} onClick={() => void calculateMatches().catch(() => {})}>
        {scoresStale ? 'Recalculer ma compatibilité' : 'Calculer ma compatibilité'}
      </Button>
    )} />
    <PageBody className="space-y-5">
      {!profileLoading && !records.skills.length && <Note>Ajoutez vos compétences pour voir votre compatibilité avec chaque offre. <Link to="/candidat/profil?section=skills" className="font-medium text-teal">Ajouter des compétences</Link></Note>}
      <Panel><div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Mots-clés"><Input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></Field>
        <Field label="Gouvernorat"><Select value={governorate} onChange={(event) => setGovernorate(event.target.value)}><option value="">Tous</option>{GOUVERNORATS.map((value) => <option key={value}>{value}</option>)}</Select></Field>
        <Field label="Contrat"><Select value={contract} onChange={(event) => setContract(event.target.value)}><option value="">Tous</option>{CONTRACT_OPTIONS.map((value) => <option key={value} value={value}>{contractLabel(value)}</option>)}</Select></Field>
        <Field label="Mode de dépôt"><Select value={mode} onChange={(event) => setMode(event.target.value)}><option value="">Tous</option><option value="platform">Sur la plateforme</option><option value="external">Site de l’employeur</option></Select></Field>
      </div></Panel>
      {loading && <Panel><Loading /></Panel>}
      {error && <p role="alert" className="text-coral">{error}</p>}
      <p className="text-sm text-slate">{results.length} offre{results.length > 1 ? 's' : ''}</p>
      {results.length ? <div className="grid gap-3 lg:grid-cols-2">{results.map((offer) => <article key={offer.id} className="rounded-[10px] border border-line bg-white p-5 shadow-panel"><Link to={`/candidat/offres/${offer.id}`} className="font-semibold text-navy hover:text-teal">{offer.title}</Link><p className="text-sm text-slate">{offer.company_name || offer.organization_name} · {offer.city || offer.governorate}</p><p className="mt-2 text-sm">{contractLabel(offer.contract_type)} · {labelFor(WORK_MODE_LABEL, offer.work_mode)}</p><p className="text-sm text-slate">{offer.easy_apply ? 'Candidature sur la plateforme' : 'Dépôt externe'}{offer.application_deadline && ` · clôture le ${formatDate(offer.application_deadline)}`}</p><MatchBadge offerId={offer.id} /></article>)}</div> : <Panel><EmptyState title="Aucune offre ne correspond à ces filtres" action={<Button size="sm" variant="secondaire" onClick={() => { setSearch(''); setGovernorate(''); setContract(''); setMode('') }}>Effacer les filtres</Button>} /></Panel>}
    </PageBody>
  </>
}
