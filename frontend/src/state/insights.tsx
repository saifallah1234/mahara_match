import { useEffect, useState } from 'react'
import * as api from '../api/matching'

let matchesCache: Promise<api.OfferMatch[]> | null = null

export function useOfferMatches() {
  const [matches, setMatches] = useState<api.OfferMatch[]>([])
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    matchesCache ??= api.listOfferMatches().catch(() => { matchesCache = null; return [] })
    void matchesCache.then(setMatches).finally(() => setLoading(false))
  }, [])
  return { matches, loading, byOffer: new Map(matches.map((m) => [m.offer_id, m])) }
}
