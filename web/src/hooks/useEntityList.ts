import { useInfiniteQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import type { ModelsResponse, ProvidersResponse, ProjectsResponse } from '../types'

const PAGE_SIZE = 20

type ModelListParams = {
  days: number
  sourceScope: string
  providerId?: string
}

export function useModelList({ days, sourceScope, providerId }: ModelListParams) {
  return useInfiniteQuery({
    queryKey: ['models-infinite', days, providerId, sourceScope],
    queryFn: ({ pageParam }: { pageParam: number }) => {
      const params: Record<string, string | number> = {
        days,
        source_scope: sourceScope,
        offset: pageParam,
        limit: PAGE_SIZE,
      }
      if (providerId) params.provider = providerId
      return fetchApi<ModelsResponse>('/models', params)
    },
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.models?.length ?? 0
      if (loaded === 0) return undefined
      const next = lastPage.models_offset + loaded
      return next < lastPage.total_models ? next : undefined
    },
    initialPageParam: 0,
  })
}

type ProviderListParams = {
  days: number
  sourceScope: string
}

export function useProviderList({ days, sourceScope }: ProviderListParams) {
  return useInfiniteQuery({
    queryKey: ['providers-infinite', days, sourceScope],
    queryFn: ({ pageParam }: { pageParam: number }) =>
      fetchApi<ProvidersResponse>('/providers', {
        days,
        source_scope: sourceScope,
        offset: pageParam,
        limit: PAGE_SIZE,
      }),
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.providers?.length ?? 0
      if (loaded === 0) return undefined
      const next = lastPage.providers_offset + loaded
      return next < lastPage.total_providers ? next : undefined
    },
    initialPageParam: 0,
  })
}

type ProjectListParams = {
  days: number
  sourceScope: string
}

export function useProjectList({ days, sourceScope }: ProjectListParams) {
  return useInfiniteQuery({
    queryKey: ['projects-infinite', days, sourceScope],
    queryFn: ({ pageParam }: { pageParam: number }) =>
      fetchApi<ProjectsResponse>('/projects', {
        days,
        source_scope: sourceScope,
        offset: pageParam,
        limit: PAGE_SIZE,
      }),
    getNextPageParam: (lastPage) => {
      const loaded = lastPage.projects?.length ?? 0
      if (loaded === 0) return undefined
      const next = lastPage.projects_offset + loaded
      return next < lastPage.total_projects ? next : undefined
    },
    initialPageParam: 0,
  })
}
