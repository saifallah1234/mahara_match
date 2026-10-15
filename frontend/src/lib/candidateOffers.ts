import type { Offer } from '../api/candidate'

export function filterCandidateOffers(offers: Offer[], contract: string, mode: string): Offer[] {
  return offers.filter((offer) =>
    (!contract || offer.contract_type === contract) &&
    (!mode || (mode === 'platform' ? offer.easy_apply : !offer.easy_apply)),
  )
}
