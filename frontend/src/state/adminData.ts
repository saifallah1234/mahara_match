import { useCallback, useEffect, useRef, useState } from 'react'
import * as api from '../api/admin'
import { listSkills, type SkillRef } from '../api/recruiter'

function useLoad<T>(load: () => Promise<T>, empty: T) {
  const [data, setData] = useState<T>(empty)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const reload = useCallback(async () => {
    setLoading(true); setError(null)
    try { setData(await load()) }
    catch (e) { setError(e instanceof Error ? e.message : 'Chargement impossible.') }
    finally { setLoading(false) }
  }, [load])
  useEffect(() => { void reload() }, [reload])
  return { data, loading, error, reload }
}

/**
 * Liste paginée avec « Charger plus ». Recharge la première page quand `resetKey` change (filtre, lot).
 * `load` peut être une closure neuve à chaque rendu : on la lit par référence pour ne pas boucler.
 */
export function usePagedList<T>(load: (page: number) => Promise<api.Paged<T>>, resetKey: string) {
  const [data, setData] = useState<T[]>([])
  const [count, setCount] = useState(0)
  const [page, setPage] = useState(0)
  const [hasMore, setHasMore] = useState(false)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const loader = useRef(load)
  loader.current = load
  const latest = useRef(0)

  const fetchPage = useCallback(async (n: number) => {
    const request = ++latest.current
    setLoading(true); setError(null)
    try {
      const result = await loader.current(n)
      if (request !== latest.current) return // une réponse périmée (autre filtre ou lot) ne remplace pas la liste
      setData((previous) => (n === 1 ? result.items : [...previous, ...result.items]))
      setCount(result.count); setHasMore(result.hasMore); setPage(n)
    } catch (e) { setError(e instanceof Error ? e.message : 'Chargement impossible.') }
    finally { setLoading(false) }
  }, [])

  useEffect(() => { void fetchPage(1) }, [fetchPage, resetKey])
  return { data, count, hasMore, loading, error, loadMore: () => fetchPage(page + 1) }
}

const none = { skills: [] as SkillRef[] }
export const useAuditLogs = () => usePagedList(api.listAuditPage, 'audit')
export const useSources = () => useLoad(api.listSources, [] as api.DataSource[])
export const useBatches = () => usePagedList(api.listBatchPage, 'batches')
export const useBatchRows = (batchId: string, status: string) =>
  usePagedList((page) => api.listBatchRowPage(batchId, status, page), `rows:${batchId}:${status}`)
export const useSkillCatalog = () => useLoad(listSkills, none.skills)
