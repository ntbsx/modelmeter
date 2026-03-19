import { useState } from 'react'
import { ChevronDown, ChevronUp, RefreshCw, AlertTriangle } from 'lucide-react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { cn } from '../lib/utils'
import type { SourceScopeValue } from '../hooks/useSourceScope'

export interface SourceStatusBannerProps {
  isLoading: boolean
  isFetching?: boolean
  sourceScope: SourceScopeValue
  sourcesConsidered?: string[]
  sourcesSucceeded?: string[]
  sourcesFailed?: Array<Record<string, string>>
  hasData: boolean
  healthCheckSupport?: boolean
}

export default function SourceStatusBanner({
  isLoading,
  isFetching = false,
  sourceScope,
  sourcesConsidered = [],
  sourcesSucceeded = [],
  sourcesFailed = [],
  hasData,
  healthCheckSupport = true,
}: SourceStatusBannerProps) {
  const [expanded, setExpanded] = useState(false)
  const queryClient = useQueryClient()

  const healthCheckMutation = useMutation({
    mutationFn: async () => {
      const response = await fetchApi('/sources/check')
      return response
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sources'] })
      queryClient.invalidateQueries({ queryKey: ['sources', 'health'] })
    },
  })

  const isRefetching = isFetching && !isLoading
  const failedSources = sourcesFailed.length > 0
  const allFailed = sourcesSucceeded.length === 0 && failedSources
  const partialFailure = sourcesSucceeded.length > 0 && failedSources
  const hasEmptyData = !isLoading && !isRefetching && !hasData

  if (!isLoading && !isRefetching && !failedSources && hasData && sourceScope === 'self') {
    return null
  }

  let bannerVariant: 'loading' | 'warning' | 'error' | 'info' = 'info'
  let message = ''
  let showHealthCheck = false

  if (isLoading) {
    bannerVariant = 'loading'
    message = 'Loading data...'
  } else if (isRefetching) {
    bannerVariant = 'loading'
    const sourceCount = sourcesConsidered.length
    message = sourceCount > 1 ? `Loading data from ${sourceCount} sources...` : 'Refreshing data...'
  } else if (allFailed) {
    bannerVariant = 'error'
    message = `Unable to reach ${sourcesConsidered.length > 1 ? 'any sources' : 'the selected source'}`
    showHealthCheck = healthCheckSupport
  } else if (partialFailure) {
    bannerVariant = 'warning'
    const failedCount = sourcesFailed.length
    message = `Unable to reach ${failedCount} ${failedCount === 1 ? 'source' : 'sources'}`
    showHealthCheck = healthCheckSupport
  } else if (hasEmptyData) {
    bannerVariant = 'info'
    message = 'No data available for the selected time range'
  }

  const baseClasses = cn(
    'mb-6 rounded-lg border px-4 py-3 text-sm',
    'transition-all duration-300',
    isRefetching && 'animate-pulse'
  )

  const variantClasses = {
    loading: 'border-blue-200 bg-blue-50 text-blue-800 dark:border-blue-800/50 dark:bg-blue-900/20 dark:text-blue-300',
    warning: 'border-amber-200 bg-amber-50 text-amber-800 dark:border-amber-800/50 dark:bg-amber-900/20 dark:text-amber-300',
    error: 'border-red-200 bg-red-50 text-red-800 dark:border-red-800/50 dark:bg-red-900/20 dark:text-red-300',
    info: 'border-gray-200 bg-gray-50 text-gray-700 dark:border-gray-800/50 dark:bg-gray-900/20 dark:text-gray-300',
  }

  return (
    <div className={cn(baseClasses, variantClasses[bannerVariant])}>
      <div className="flex items-start gap-3">
        <div className="flex-1">
          <p className="font-medium">{message}</p>

          {partialFailure && sourcesFailed.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="mt-2 flex items-center gap-1 text-xs font-semibold opacity-80 hover:opacity-100 transition-opacity"
              type="button"
            >
              {expanded ? (
                <>
                  Hide details
                  <ChevronUp className="h-3 w-3" />
                </>
              ) : (
                <>
                  Show details
                  <ChevronDown className="h-3 w-3" />
                </>
              )}
            </button>
          )}

          {expanded && partialFailure && sourcesFailed.length > 0 && (
            <div className="mt-2 space-y-1">
              {sourcesFailed.map((source, index) => {
                const [sourceId, error] = Object.entries(source)[0] ?? []
                return (
                  <div key={index} className="text-xs opacity-90 flex items-start gap-1.5">
                    <span className="font-medium">{sourceId}:</span>
                    <span>{error || 'Connection failed'}</span>
                  </div>
                )
              })}
            </div>
          )}
        </div>

        {showHealthCheck && bannerVariant !== 'loading' && (
          <button
            onClick={() => healthCheckMutation.mutate()}
            disabled={healthCheckMutation.isPending}
            className="shrink-0 rounded-md border border-current px-3 py-1.5 text-xs font-medium hover:bg-white/10 dark:hover:bg-black/10 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center gap-1.5"
            type="button"
          >
            {healthCheckMutation.isPending ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <AlertTriangle className="h-3.5 w-3.5" />
            )}
            Check sources
          </button>
        )}
      </div>
    </div>
  )
}
