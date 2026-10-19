import { useCallback, useEffect, useState } from 'react'
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

const none = { audit: [] as api.AuditLog[], sources: [] as api.DataSource[], batches: [] as api.ImportBatch[], skills: [] as SkillRef[] }
export const useAuditLogs = () => useLoad(api.listAuditLogs, none.audit)
export const useSources = () => useLoad(api.listSources, none.sources)
export const useBatches = () => useLoad(api.listBatches, none.batches)
export const useSkillCatalog = () => useLoad(listSkills, none.skills)