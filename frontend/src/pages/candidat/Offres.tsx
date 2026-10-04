import { useMemo, useState } from 'react'
import { PageBody, PageHeader } from '../../components/layout'
import { EmptyState, Field, Panel, Select, Input } from '../../components/ui'
import { OfferCard } from '../../components/domain'
import { useStore } from '../../state/store'
import { rankOffers } from '../../lib/matching'
import { CONTRACT_LABEL, GOUVERNORATS } from '../../lib/format'
import type { ContractType } from '../../lib/types'

export default function CandidatOffres() {
  const { currentProfile, offers, skills, organizationOf } = useStore()
  const [keywords, setKeywords] = useState('')
  const [governorate, setGovernorate] = useState('')
  const [contract, setContract] = useState('')
  const [onlyEasyApply, setOnlyEasyApply] = useState(false)

  const results = useMemo(() => {
    if (!currentProfile) return []
    const term = keywords.trim().toLowerCase()
    return rankOffers(currentProfile, offers, skills).filter(({ offer }) => {
      if (governorate && offer.governorate !== governorate) return false
      if (contract && offer.contractType !== contract) return false
      if (onlyEasyApply && !offer.easyApply) return false
      if (!term) return true
      const haystack = `${offer.title} ${offer.description} ${organizationOf(offer.organizationId)?.legalName ?? ''}`
      return haystack.toLowerCase().includes(term)
    })
  }, [currentProfile, offers, skills, keywords, governorate, contract, onlyEasyApply, organizationOf])

  if (!currentProfile) return null

  return (
    <>
      <PageHeader
        title="Offres d’emploi"
      />

      <PageBody className="space-y-5">
        <Panel>
          <div className="grid gap-4 p-5 sm:grid-cols-2 lg:grid-cols-4">
            <Field label="Mots-clés">
              <Input
                value={keywords}
                onChange={(e) => setKeywords(e.target.value)}
                placeholder="Intitulé, entreprise…"
                type="search"
              />
            </Field>
            <Field label="Gouvernorat">
              <Select value={governorate} onChange={(e) => setGovernorate(e.target.value)}>
                <option value="">Tous</option>
                {GOUVERNORATS.map((g) => (
                  <option key={g}>{g}</option>
                ))}
              </Select>
            </Field>
            <Field label="Type de contrat">
              <Select value={contract} onChange={(e) => setContract(e.target.value)}>
                <option value="">Tous</option>
                {(Object.keys(CONTRACT_LABEL) as ContractType[]).map((type) => (
                  <option key={type} value={type}>
                    {CONTRACT_LABEL[type]}
                  </option>
                ))}
              </Select>
            </Field>
            <Field label="Mode de dépôt">
              <Select value={onlyEasyApply ? 'easy' : ''} onChange={(e) => setOnlyEasyApply(e.target.value === 'easy')}>
                <option value="">Tous</option>
                <option value="easy">Candidature sur la plateforme</option>
              </Select>
            </Field>
          </div>
        </Panel>

        <p className="text-[13px] text-slate">
          {results.length} offre{results.length > 1 ? 's' : ''} ouverte{results.length > 1 ? 's' : ''}
          {results.length > 0 && ' · classées par couverture de compétences'}
        </p>

        {results.length === 0 ? (
          <Panel>
            <EmptyState title="Aucune offre ne correspond à ces filtres">
              Élargissez le gouvernorat ou retirez un filtre pour voir davantage de résultats.
            </EmptyState>
          </Panel>
        ) : (
          <div className="grid gap-3 lg:grid-cols-2">
            {results.map(({ offer, match }) => (
              <OfferCard
                key={offer.id}
                offer={offer}
                organizationName={organizationOf(offer.organizationId)?.legalName ?? '—'}
                match={match}
                to={`/candidat/offres/${offer.id}`}
              />
            ))}
          </div>
        )}
      </PageBody>
    </>
  )
}
