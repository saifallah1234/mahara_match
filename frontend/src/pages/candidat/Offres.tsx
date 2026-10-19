import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { PageBody, PageHeader } from '../../components/layout'
import { EmptyState, Field, Input, Panel, Select } from '../../components/ui'
import { publishedOffers, type Offer } from '../../api/candidate'
import { filterCandidateOffers } from '../../lib/candidateOffers'
import { useCandidate } from '../../state/candidate'
import { CONTRACT_LABEL, GOUVERNORATS, WORK_MODE_LABEL, formatDate } from '../../lib/format'
import type { ContractType, WorkMode } from '../../lib/types'
import { MatchBadge } from '../../components/insights'

export default function CandidatOffres() {
  const { offers: initial } = useCandidate()
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
  const contracts = [...new Set(initial.map((offer) => offer.contract_type).filter(Boolean))]
  return <>
    <PageHeader title="Offres d’emploi" />
    <PageBody className="space-y-5">
      <Panel><div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
        <Field label="Mots-clés"><Input type="search" value={search} onChange={(event) => setSearch(event.target.value)} /></Field>
        <Field label="Gouvernorat"><Select value={governorate} onChange={(event) => setGovernorate(event.target.value)}><option value="">Tous</option>{GOUVERNORATS.map((value) => <option key={value}>{value}</option>)}</Select></Field>
        <Field label="Contrat"><Select value={contract} onChange={(event) => setContract(event.target.value)}><option value="">Tous</option>{contracts.map((value) => <option key={value}>{value}</option>)}</Select></Field>
        <Field label="Mode de dépôt"><Select value={mode} onChange={(event) => setMode(event.target.value)}><option value="">Tous</option><option value="platform">Sur la plateforme</option><option value="external">Site de l’employeur</option></Select></Field>
      </div></Panel>
      {loading && <p role="status">Recherche en cours…</p>}
      {error && <p role="alert" className="text-coral">{error}</p>}
      <p className="text-sm text-slate">{results.length} offre{results.length > 1 ? 's' : ''}</p>
      {results.length ? <div className="grid gap-3 lg:grid-cols-2">{results.map((offer) => <article key={offer.id} className="rounded-[10px] border border-line bg-white p-5 shadow-panel"><Link to={`/candidat/offres/${offer.id}`} className="font-semibold text-navy hover:text-teal">{offer.title}</Link><p className="text-sm text-slate">{offer.organization_name} · {offer.city || offer.governorate}</p><p className="mt-2 text-sm">{CONTRACT_LABEL[offer.contract_type as ContractType] || offer.contract_type || 'Contrat non renseigné'} · {WORK_MODE_LABEL[offer.work_mode as WorkMode] || offer.work_mode || 'Mode non renseigné'}</p><p className="text-sm text-slate">{offer.easy_apply ? 'Candidature sur la plateforme' : 'Dépôt externe'}{offer.application_deadline && ` · clôture le ${formatDate(offer.application_deadline)}`}</p><MatchBadge offerId={offer.id} /></article>)}</div> : <Panel><EmptyState title="Aucune offre ne correspond à ces filtres" /></Panel>}
    </PageBody>
  </>
}
