import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd, cn } from '../lib/utils'
import type { ProvidersResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { PageHeader } from '../components/DataTable'
import { Badge } from '../components/ui'
import SourceStatusBanner from '../components/SourceStatusBanner'

export default function Providers() {
  const { days } = useDaysFilter()
  const { sourceScope } = useSourceScope()

  const { data, isLoading, isFetching } = useQuery<ProvidersResponse>({
    queryKey: ['providers', days, sourceScope],
    queryFn: () => fetchApi('/providers', { days, source_scope: sourceScope }),
  })

  const isRefetching = isFetching && !isLoading
  const hasData = (data?.providers ?? []).length > 0

  if (isLoading) return <PageLoading title="Providers" subtitle="Loading provider usage" cards={3} />
  if (!data) {
    return (
      <PageErrorState
        title="Unable to load providers"
        description="We could not fetch provider usage right now. Try refreshing the page."
      />
    )
  }

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <PageHeader
        title="Providers"
        description={`Usage breakdown by provider (${days === 1 ? 'last 24 hours' : `last ${days} days`})`}
      />

      <SourceStatusBanner
        isLoading={isLoading}
        isFetching={isRefetching}
        sourceScope={sourceScope}
        sourcesConsidered={data?.sources_considered ?? []}
        sourcesSucceeded={data?.sources_succeeded ?? []}
        sourcesFailed={data?.sources_failed ?? []}
        hasData={hasData}
      />

      <div className={cn('ds-surface overflow-hidden transition-opacity', isRefetching && 'opacity-60')}>

      <div className="ds-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-[var(--border-default)]">
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] whitespace-nowrap">Provider</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Models</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Interactions</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {(data.providers ?? []).map((provider) => (
                <tr key={provider.provider} className="hover:bg-[var(--surface-accent)]/50 transition-colors">
                  <td className="px-4 sm:px-6 py-4 font-medium whitespace-nowrap text-[var(--text-primary)]">
                    <Link
                      to={`/models/provider/${encodeURIComponent(provider.provider)}`}
                      className="text-[var(--accent-primary)] hover:text-[var(--accent-primary-hover)] hover:underline transition-colors"
                    >
                      {provider.provider}
                    </Link>
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">
                    <Badge variant="default">{provider.total_models}</Badge>
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">
                    {provider.total_interactions}
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">
                    {formatTokens(provider.usage.total_tokens)}
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">
                    {provider.cost_usd ? formatUsd(provider.cost_usd) : '-'}
                  </td>
                </tr>
              ))}
              {(data.providers ?? []).length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 sm:px-6 py-12 text-center text-[var(--text-tertiary)]">
                    No provider usage found in this period.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
        </div>
      </div>
    </div>
  )
}
