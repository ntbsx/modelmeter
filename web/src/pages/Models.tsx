import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ModelsResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'

export default function Models() {
  const { providerId } = useParams<{ providerId: string }>()
  const { days } = useDaysFilter()
  const { sourceScope } = useSourceScope()

  const { data, isLoading } = useQuery<ModelsResponse>({
    queryKey: ['models', days, providerId, sourceScope],
    queryFn: () =>
      fetchApi(
        '/models',
        providerId
          ? { days, provider: providerId, source_scope: sourceScope }
          : { days, source_scope: sourceScope }
      )
  })

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
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto space-y-6 w-full min-w-0">
      <div className="space-y-3">
        <Link 
          to="/models" 
          className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Providers
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white break-all">
              {providerId ? `${providerId} Models` : 'Models'}
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Usage breakdown by model ({days === 1 ? 'last 24 hours' : `last ${days} days`})
            </p>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">Model</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Sessions</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Interactions</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Input</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Output</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {(data.models ?? []).map((m) => (
                <tr key={m.model_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">
                    <Link
                      to={`/models/${encodeURIComponent(m.model_id)}`}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                    >
                      {m.model_id}
                    </Link>
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">{m.total_sessions}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">{m.total_interactions}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">{formatTokens(m.usage.input_tokens)}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">{formatTokens(m.usage.output_tokens)}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">{formatTokens(m.usage.total_tokens)}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">{m.cost_usd ? formatUsd(m.cost_usd) : '-'}</td>
                </tr>
              ))}
              {(data.models ?? []).length === 0 && (
                <tr>
                  <td colSpan={7} className="px-3 sm:px-6 py-8 text-center text-gray-500 dark:text-gray-400">No model usage found in this period.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
