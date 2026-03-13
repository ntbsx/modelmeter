import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ModelsResponse } from '../types'

export default function Models() {
  const { data, isLoading } = useQuery<ModelsResponse>({
    queryKey: ['models'],
    queryFn: () => fetchApi('/models', { days: 7 })
  })

  if (isLoading) return <div className="p-8 text-gray-500 dark:text-gray-400">Loading...</div>
  if (!data) return <div className="p-8 text-red-500 dark:text-red-400">Failed to load models.</div>

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Models</h1>
        <p className="text-gray-500 dark:text-gray-400">Usage breakdown by model (last 7 days)</p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-6 py-4 font-medium whitespace-nowrap">Model</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Sessions</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Interactions</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Input</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Output</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data.models.map((m) => (
                <tr key={m.model_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-6 py-4 font-medium text-gray-900 dark:text-gray-100 whitespace-nowrap">{m.model_id}</td>
                  <td className="px-6 py-4 text-right text-gray-600 dark:text-gray-400">{m.total_sessions}</td>
                  <td className="px-6 py-4 text-right text-gray-600 dark:text-gray-400">{m.total_interactions}</td>
                  <td className="px-6 py-4 text-right text-gray-600 dark:text-gray-400">{formatTokens(m.usage.input_tokens)}</td>
                  <td className="px-6 py-4 text-right text-gray-600 dark:text-gray-400">{formatTokens(m.usage.output_tokens)}</td>
                  <td className="px-6 py-4 text-right font-mono text-gray-900 dark:text-gray-100">{formatTokens(m.usage.total_tokens)}</td>
                  <td className="px-6 py-4 text-right font-mono text-gray-900 dark:text-gray-100">{m.cost_usd ? formatUsd(m.cost_usd) : '-'}</td>
                </tr>
              ))}
              {data.models.length === 0 && (
                <tr>
                  <td colSpan={7} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">No model usage found in this period.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
