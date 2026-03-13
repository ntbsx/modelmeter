import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, Folder } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ProjectDetailResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageEmptyState, PageErrorState } from '../components/PageState'

export default function ProjectDetail() {
  const { projectId } = useParams()
  const decodedProjectId = decodeURIComponent(projectId ?? '')

  const { data, isLoading, error } = useQuery<ProjectDetailResponse>({
    queryKey: ['project-detail', decodedProjectId],
    queryFn: () => fetchApi(`/projects/${encodeURIComponent(decodedProjectId)}`, { days: 7 }),
    enabled: decodedProjectId.length > 0,
  })

  if (!decodedProjectId) {
    return (
      <PageErrorState
        title="Invalid project ID"
        description="The requested project identifier is not valid."
        action={
          <Link
            className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            to="/projects"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </Link>
        }
      />
    )
  }

  if (isLoading) {
    return <PageLoading title="Project Detail" subtitle="Loading project sessions" cards={3} />
  }

  if (error) {
    return (
      <PageErrorState
        title="Unable to load project details"
        description="We could not fetch sessions for this project. Please refresh and try again."
        action={
          <Link
            className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            to="/projects"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </Link>
        }
      />
    )
  }

  if (!data) {
    return (
      <PageEmptyState
        title="Project not found"
        description="No usage data was found for this project in the selected window."
        action={
          <Link
            className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            to="/projects"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Projects
          </Link>
        }
      />
    )
  }

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto space-y-6 w-full min-w-0">
      <div className="space-y-3">
        <Link
          className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          to="/projects"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Projects
        </Link>

        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">
            {data.project_name}
          </h1>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-2 min-w-0">
            <Folder className="h-4 w-4 shrink-0" />
            <span className="truncate">{data.project_path || data.project_id}</span>
          </div>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Session activity for the last 7 days.</p>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Sessions</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">
            {data.total_sessions}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Total Tokens</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">
            {formatTokens(data.usage.total_tokens)}
          </div>
        </div>
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Cost</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">
            {data.total_cost_usd ? formatUsd(data.total_cost_usd) : 'N/A'}
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm min-w-[720px]">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">Session</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium whitespace-nowrap">Directory</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Interactions</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Tokens</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Cost</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right whitespace-nowrap">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data.sessions.map((session) => (
                <tr key={session.session_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-3 sm:px-6 py-3 sm:py-4">
                    <div
                      className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-[16rem]"
                      title={session.title || session.session_id}
                    >
                      {session.title || session.session_id}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-[16rem]" title={session.session_id}>
                      {session.session_id}
                    </div>
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-gray-600 dark:text-gray-400">
                    <span className="truncate block max-w-[18rem]" title={session.directory || '-'}>
                      {session.directory || '-'}
                    </span>
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400">
                    {session.total_interactions}
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">
                    {formatTokens(session.usage.total_tokens)}
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right font-mono text-gray-900 dark:text-gray-100">
                    {session.cost_usd ? formatUsd(session.cost_usd) : '-'}
                  </td>
                  <td className="px-3 sm:px-6 py-3 sm:py-4 text-right text-gray-600 dark:text-gray-400 whitespace-nowrap">
                    <span className="inline-flex items-center gap-1 justify-end">
                      <Clock className="h-3.5 w-3.5" />
                      {new Date(session.last_updated_ms).toLocaleString()}
                    </span>
                  </td>
                </tr>
              ))}
              {data.sessions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-3 sm:px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                    No session activity found in this period.
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
