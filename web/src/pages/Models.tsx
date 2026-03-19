import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd, cn } from '../lib/utils'
import type { ModelsResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import SourceStatusBanner from '../components/SourceStatusBanner'

export default function Models() {
  const { providerId } = useParams<{ providerId: string }>()
  const { days } = useDaysFilter()
  const { sourceScope } = useSourceScope()

  const { data, isLoading, isFetching } = useQuery<ModelsResponse>({
    queryKey: ['models', days, providerId, sourceScope],
    queryFn: () =>
      fetchApi(
        '/models',
        providerId
          ? { days, provider: providerId, source_scope: sourceScope }
          : { days, source_scope: sourceScope }
      )
  })

  const isRefetching = isFetching && !isLoading
  const hasData = (data?.models ?? []).length > 0

  if (isLoading) return <PageLoading title="Models" subtitle="Loading model usage" cards={3} />
  if (!data) {
    return (
      <PageErrorState
        title="Unable to load models"
        description="We could not fetch model usage right now. Try refreshing the page."
      />
    )
  }

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <div className="mb-10 sm:mb-12 space-y-4">
        <Link
          to="/models"
          className="inline-flex items-center gap-2 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Providers
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)] break-all">
              {providerId ? `${providerId} Models` : 'Models'}
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              Usage breakdown by model ({days === 1 ? 'last 24 hours' : `last ${days} days`})
            </p>
          </div>
        </div>
      </div>

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
            <thead className="bg-[var(--surface-secondary)] border-b border-[var(--border-default)]">
              <tr>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] whitespace-nowrap">Model</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Sessions</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Interactions</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Input</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Output</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {(data.models ?? []).map((m) => (
                <tr key={m.model_id} className="hover:bg-[var(--surface-accent)]/50 transition-colors">
                  <td className="px-4 sm:px-6 py-4 font-medium whitespace-nowrap">
                    <Link
                      to={`/models/${encodeURIComponent(m.model_id)}`}
                      className="text-[var(--accent-primary)] hover:text-[var(--accent-primary-hover)] hover:underline"
                    >
                      {m.model_id}
                    </Link>
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">{m.total_sessions}</td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">{m.total_interactions}</td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">{formatTokens(m.usage.input_tokens)}</td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">{formatTokens(m.usage.output_tokens)}</td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">{formatTokens(m.usage.total_tokens)}</td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">{m.cost_usd ? formatUsd(m.cost_usd) : '-'}</td>
                </tr>
              ))}
              {(data.models ?? []).length === 0 && (
                <tr>
                  <td colSpan={7} className="px-4 sm:px-6 py-12 text-center text-[var(--text-tertiary)]">No model usage found in this period.</td>
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
