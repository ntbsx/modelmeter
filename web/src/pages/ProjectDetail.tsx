import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { ArrowLeft, Clock, Folder, Info } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ProjectDetailResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageEmptyState, PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'

export default function ProjectDetail() {
  const { projectId } = useParams()
  const decodedProjectId = decodeURIComponent(projectId ?? '')
  const { sourceScope } = useSourceScope()
  const detailScope = 'self' as const
  const [searchTerm, setSearchTerm] = useState('')
  const [sortBy, setSortBy] = useState<'last_updated' | 'tokens' | 'cost' | 'interactions'>(
    'last_updated'
  )

  const { data, isLoading, error } = useQuery<ProjectDetailResponse>({
    queryKey: ['project-detail', decodedProjectId, detailScope],
    queryFn: () =>
      fetchApi(`/projects/${encodeURIComponent(decodedProjectId)}`, {
        source_scope: detailScope,
      }),
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

  const normalizedSearch = searchTerm.trim().toLowerCase()
  const looksLikePath = data.project_name.includes('/') || data.project_name.includes('\\')
  const displayProjectName =
    data.project_path && data.project_name === data.project_path
      ? data.project_name.split(/[\\/]/).filter(Boolean).pop() || data.project_id
      : looksLikePath
        ? data.project_name.split(/[\\/]/).filter(Boolean).pop() || data.project_name
        : data.project_name
  const visibleSessions = (data.sessions ?? [])
    .filter((session) => {
      if (normalizedSearch.length === 0) {
        return true
      }

      const haystack = [session.session_id, session.title ?? '', session.directory ?? '']
        .join(' ')
        .toLowerCase()

      return haystack.includes(normalizedSearch)
    })
    .sort((a, b) => {
      if (sortBy === 'tokens') {
        return b.usage.total_tokens - a.usage.total_tokens
      }
      if (sortBy === 'cost') {
        return (b.cost_usd ?? 0) - (a.cost_usd ?? 0)
      }
      if (sortBy === 'interactions') {
        return b.total_interactions - a.total_interactions
      }

      return b.last_updated_ms - a.last_updated_ms
    })

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <div className="mb-8 sm:mb-10 space-y-3">
        <Link
          className="inline-flex items-center gap-2 text-sm text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          to="/projects"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Projects
        </Link>

        <div className="min-w-0">
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)]">
            {displayProjectName}
          </h1>
          <div className="text-sm text-[var(--text-secondary)] mt-1.5 flex items-center gap-2 min-w-0">
            <Folder className="h-4 w-4 shrink-0" />
            <span className="truncate">{data.project_path || data.project_id}</span>
          </div>
          <p className="text-[var(--text-secondary)] mt-2">
            Session activity across all available history.
          </p>
          </div>
      </div>

      {sourceScope !== 'self' && (
        <div className="mb-6 flex items-start gap-3 rounded-lg border border-[var(--border-default)] bg-[var(--surface-secondary)] px-4 py-3 text-sm text-[var(--text-secondary)]">
          <Info className="h-4 w-4 shrink-0 mt-0.5 text-[var(--text-tertiary)]" />
          <span>Project detail always shows data from this server only — federated project detail is not yet supported. The source scope selector does not affect this view.</span>
        </div>
      )}

      <section className="mb-8 sm:mb-10">
        <div className="grid grid-cols-3 gap-4 sm:gap-5">
          <div className="ds-surface p-5 sm:p-6">
            <div className="ds-text-label">Sessions</div>
            <div className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)] mt-1 ds-text-tabular">
              {data.total_sessions}
            </div>
          </div>
          <div className="ds-surface p-5 sm:p-6">
            <div className="ds-text-label">Total Tokens</div>
            <div className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)] mt-1 ds-text-tabular">
              {formatTokens(data.usage.total_tokens)}
            </div>
          </div>
          <div className="ds-surface p-5 sm:p-6">
            <div className="ds-text-label">Cost</div>
            <div className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)] mt-1 ds-text-tabular">
              {data.total_cost_usd ? formatUsd(data.total_cost_usd) : 'N/A'}
            </div>
          </div>
        </div>
      </section>

      <div className="ds-surface overflow-hidden">
        <div className="p-4 sm:px-6 sm:py-5 border-b border-[var(--border-subtle)] flex flex-col sm:flex-row gap-3 sm:items-center sm:justify-between">
          <input
            className="w-full sm:max-w-xs rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:ring-2 focus:ring-blue-500/40"
            onChange={(event) => setSearchTerm(event.target.value)}
            placeholder="Search sessions..."
            type="search"
            value={searchTerm}
          />
          <select
            className="rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:ring-2 focus:ring-blue-500/40"
            onChange={(event) =>
              setSortBy(
                event.target.value as 'last_updated' | 'tokens' | 'cost' | 'interactions'
              )
            }
            value={sortBy}
          >
            <option value="last_updated">Last Updated</option>
            <option value="tokens">Tokens</option>
            <option value="cost">Cost</option>
            <option value="interactions">Interactions</option>
          </select>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm min-w-[720px]">
            <thead className="border-b border-[var(--border-default)]">
              <tr>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] whitespace-nowrap">Session</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] whitespace-nowrap">Directory</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Interactions</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Tokens</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Cost</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] text-right whitespace-nowrap">Last Updated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {visibleSessions.map((session) => (
                <tr key={session.session_id} className="hover:bg-[var(--surface-accent)]/50 transition-colors">
                  <td className="px-4 sm:px-6 py-4">
                    <div
                      className="font-medium text-[var(--text-primary)] truncate max-w-[14rem]"
                      title={session.title || session.session_id}
                    >
                      {session.title || session.session_id}
                    </div>
                    <div className="text-xs text-[var(--text-tertiary)] truncate max-w-[14rem]" title={session.session_id}>
                      {session.session_id}
                    </div>
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-[var(--text-secondary)]">
                    <span className="truncate block max-w-[14rem]" title={session.directory || '-'}>
                      {session.directory || '-'}
                    </span>
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">
                    {session.total_interactions}
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">
                    {formatTokens(session.usage.total_tokens)}
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">
                    {session.cost_usd ? formatUsd(session.cost_usd) : '-'}
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)] whitespace-nowrap">
                    <span className="inline-flex items-center gap-1.5 justify-end">
                      <Clock className="h-3.5 w-3.5" />
                      {new Date(session.last_updated_ms).toLocaleString()}
                    </span>
                  </td>
                </tr>
              ))}
              {visibleSessions.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 sm:px-6 py-12 text-center text-[var(--text-secondary)]">
                    No sessions match this filter.
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
