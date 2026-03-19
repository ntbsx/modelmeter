import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import type { SourceRegistryPublic } from '../types'

const SOURCE_REGISTRY_KEY = ['sources']

export function useSourceLabels() {
  const { data: registry, isLoading } = useQuery<SourceRegistryPublic>({
    queryKey: SOURCE_REGISTRY_KEY,
    queryFn: async () => {
      const response = await fetchApi('/sources')
      return response as SourceRegistryPublic
    },
    staleTime: 5 * 60 * 1000, // 5 minutes
  })

  const sourceMap = useMemo(() => {
    const map = new Map<string, string>()
    if (registry?.sources) {
      for (const source of registry.sources) {
        map.set(source.source_id, source.label || source.source_id)
      }
    }
    return map
  }, [registry])

  function getSourceLabel(sourceId: string): string {
    if (!sourceId || sourceId === 'self' || sourceId === 'local' || sourceId === '') {
      return 'This Server'
    }
    
    return sourceMap.get(sourceId) || sourceId
  }

  return { getSourceLabel, isLoading }
}
