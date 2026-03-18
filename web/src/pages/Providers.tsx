import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ProvidersResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import TimeRangeFilter from '../components/TimeRangeFilter'
import { useSourceScope } from '../hooks/useSourceScope'

export default function Providers() {
  const [days, setDays] = useState<1 | 7 | 30 | 90>(7)
  const { sourceScope } = useSourceScope()

  const { data, isLoading } = useQuery<ProvidersResponse>({
    queryKey: ['providers', days, sourceScope],
    queryFn: () => fetchApi('/providers', { days, source_scope: sourceScope }),
  })

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
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto space-y-6 w-full min-w-0">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div className="min-w-0">
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Providers</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">
            Usage breakdown by provider ({days === 1 ? 'last 24 hours' : `last ${days} days`})
          </p>
        </div>
        <TimeRangeFilter days={days} onChange={setDays} />
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">Provider</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Models</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Interactions</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data.providers.map((provider) => (
                <tr key={provider.provider} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">
                    <Link
                      to={`/models/provider/${encodeURIComponent(provider.provider)}`}
                      className="text-blue-600 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 hover:underline"
                    >
                      {provider.provider}
                    </Link>
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">
                    {provider.total_models}
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">
                    {provider.total_interactions}
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">
                    {formatTokens(provider.usage.total_tokens)}
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">
                    {provider.cost_usd ? formatUsd(provider.cost_usd) : '-'}
                  </td>
                </tr>
              ))}
              {data.providers.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 sm:px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                    No provider usage found in this period.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
