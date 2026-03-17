import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ProjectsResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import TimeRangeFilter from '../components/TimeRangeFilter'
import SourceMetaBanner from '../components/SourceMetaBanner'
import { useSourceScope } from '../hooks/useSourceScope'

export default function Projects() {
  const [days, setDays] = useState<1 | 7 | 30 | 90>(7)
  const { sourceScope } = useSourceScope()

  const { data, isLoading } = useQuery<ProjectsResponse>({
    queryKey: ['projects', days, sourceScope],
    queryFn: () => fetchApi('/projects', { days, source_scope: sourceScope })
  })

  if (isLoading) return <PageLoading title="Projects" subtitle="Loading project usage" cards={3} />
  if (!data) {
    return (
      <PageErrorState
        title="Unable to load projects"
        description="We could not fetch project usage right now. Try refreshing the page."
      />
    )
  }

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto">
      <div className="mb-6 sm:mb-8">
        <div className="flex justify-between items-end gap-3">
          <div>
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Projects</h1>
            <p className="text-gray-500 dark:text-gray-400">
              Usage breakdown by project workspace ({days === 1 ? 'last 24 hours' : `last ${days} days`})
            </p>
          </div>
          <TimeRangeFilter days={days} onChange={setDays} />
        </div>
      </div>

      <SourceMetaBanner
        sourceScope={data.source_scope}
        sourcesConsidered={data.sources_considered}
        sourcesSucceeded={data.sources_succeeded}
        sourcesFailed={data.sources_failed}
      />

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">Project</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Sessions</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Interactions</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data.projects.map((p) => (
                <tr key={p.project_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 sm:px-6 py-3 sm:py-4">
                    <Link
                      className="font-medium text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300 truncate max-w-[12rem] sm:max-w-sm block"
                      title={p.project_name}
                      to={`/projects/${encodeURIComponent(p.project_id)}`}
                    >
                      {p.project_name.split('/').pop() || p.project_name}
                    </Link>
                    <div className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[12rem] sm:max-w-sm mt-0.5" title={p.project_path || p.project_id}>
                      {p.project_path || p.project_id}
                    </div>
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">{p.total_sessions}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">{formatTokens(p.usage.total_tokens)}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">{p.total_interactions}</td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">{p.cost_usd ? formatUsd(p.cost_usd) : '-'}</td>
                </tr>
              ))}
              {data.projects.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-3 sm:px-6 py-8 text-center text-gray-500 dark:text-gray-400">No project usage found in this period.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
