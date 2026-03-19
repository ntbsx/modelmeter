import { useState } from 'react'
import { RefreshCw, Database, Wifi, WifiOff, Loader2, Info } from 'lucide-react'
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

const SourceStatusIcon = ({ variant }: { variant: 'loading' | 'warning' | 'error' | 'info' }) => {
  const iconClass = "h-4 w-4 shrink-0"
  
  switch (variant) {
    case 'loading':
      return <Loader2 className={cn(iconClass, "animate-spin")} />
    case 'warning':
      return <Wifi className={iconClass} />
    case 'error':
      return <WifiOff className={iconClass} />
    case 'info':
    default:
      return <Info className={iconClass} />
  }
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
      queryClient.invalidateQueries({ queryKey: ['sources-health-check'] })
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
    message = sourceCount > 1 ? `Loading from ${sourceCount} sources` : 'Refreshing data'
  } else if (allFailed) {
    bannerVariant = 'error'
    message = sourcesConsidered.length > 1 ? 'Unable to reach any sources' : 'Unable to reach source'
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

  if (!message) {
    return null
  }

  const variantStyles = {
    loading: {
      container: 'bg-[var(--surface-secondary)] border-[var(--border-default)]',
      icon: 'text-[var(--text-tertiary)]',
      text: 'text-[var(--text-secondary)]',
      button: 'text-[var(--accent-primary)] hover:text-[var(--accent-primary-hover)]',
    },
    warning: {
      container: 'bg-[var(--surface-warning)] border-[var(--border-warning)]',
      icon: 'text-[var(--color-warning)]',
      text: 'text-[var(--color-warning-muted-foreground)]',
      button: 'text-[var(--color-warning)] hover:opacity-80',
    },
    error: {
      container: 'bg-[var(--surface-error)] border-[var(--border-error)]',
      icon: 'text-[var(--color-error)]',
      text: 'text-[var(--color-error-muted-foreground)]',
      button: 'text-[var(--color-error)] hover:opacity-80',
    },
    info: {
      container: 'bg-[var(--surface-secondary)] border-[var(--border-default)]',
      icon: 'text-[var(--text-tertiary)]',
      text: 'text-[var(--text-secondary)]',
      button: 'text-[var(--accent-primary)] hover:text-[var(--accent-primary-hover)]',
    },
  }

  const styles = variantStyles[bannerVariant]

  return (
    <div
      className={cn(
        'mb-6 rounded-lg border px-4 py-3 text-sm',
        'transition-all duration-300',
        isRefetching && 'animate-pulse-subtle',
        styles.container
      )}
    >
      <div className="flex items-start gap-3">
        <SourceStatusIcon variant={bannerVariant} />

        <div className="flex-1 min-w-0">
          <p className={cn('font-medium', styles.text)}>{message}</p>

          {partialFailure && sourcesFailed.length > 0 && (
            <button
              onClick={() => setExpanded(!expanded)}
              className={cn(
                'mt-2 flex items-center gap-1 text-xs font-medium',
                styles.button,
                'transition-opacity'
              )}
              type="button"
            >
              {expanded ? 'Hide details' : 'Show details'}
              <svg
                className={cn('h-3 w-3 transition-transform', expanded && 'rotate-180')}
                fill="none"
                viewBox="0 0 24 24"
                stroke="currentColor"
              >
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
              </svg>
            </button>
          )}

          {expanded && partialFailure && sourcesFailed.length > 0 && (
            <div className="mt-3 space-y-2 pl-1">
              {sourcesFailed.map((source, index) => {
                const [sourceId, error] = Object.entries(source)[0] ?? []
                return (
                  <div key={index} className="flex items-start gap-2 text-xs">
                    <Database className="h-3 w-3 mt-0.5 text-[var(--text-tertiary)] shrink-0" />
                    <div>
                      <span className="font-medium text-[var(--text-primary)]">{sourceId}</span>
                      <span className="text-[var(--text-tertiary)]"> — {error || 'Connection failed'}</span>
                    </div>
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
            className={cn(
              'shrink-0 flex items-center gap-1.5 text-xs font-medium',
              styles.button,
              'transition-opacity disabled:opacity-50'
            )}
            type="button"
          >
            {healthCheckMutation.isPending ? (
              <RefreshCw className="h-3.5 w-3.5 animate-spin" />
            ) : (
              <RefreshCw className="h-3.5 w-3.5" />
            )}
            Check sources
          </button>
        )}
      </div>
    </div>
  )
}
