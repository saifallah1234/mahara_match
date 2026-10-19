import { useEffect, useState } from 'react'
import { getIndicators, type Indicators } from '../api/reporting'

export function useIndicators() {
  const [data, setData] = useState<Indicators | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  useEffect(() => {
    getIndicators().then(setData).catch((e) => setError(e instanceof Error ? e.message : 'Chargement impossible.')).finally(() => setLoading(false))
  }, [])
  return { data, loading, error, unavailable: !loading && !error && data === null }
}