import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ProjectsResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { PageHeader } from '../components/DataTable'
import { Badge } from '../components/ui'

export default function Projects() {
  const { days } = useDaysFilter()
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
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <PageHeader
        title="Projects"
        description={`Usage breakdown by project workspace (${days === 1 ? 'last 24 hours' : `last ${days} days`})`}
      />

      <div className="ds-surface overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-[var(--surface-tertiary)]/50 border-b border-[var(--border-default)]">
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-tertiary)] whitespace-nowrap">Project</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-tertiary)] text-right whitespace-nowrap">Sessions</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-tertiary)] text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-tertiary)] text-right whitespace-nowrap">Interactions</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-tertiary)] text-right whitespace-nowrap">Cost</th>
                <th className="px-4 sm:px-6 py-4 font-medium text-[var(--text-tertiary)] whitespace-nowrap">Sources</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[var(--border-subtle)]">
              {(data.projects ?? []).map((p) => (
                <tr key={p.project_id} className="hover:bg-[var(--surface-tertiary)]/30 transition-colors">
                  <td className="px-4 sm:px-6 py-4">
                    <Link
                      className="font-medium text-[var(--accent-primary)] hover:text-[var(--accent-primary-hover)] truncate max-w-[12rem] sm:max-w-xs block transition-colors"
                      title={p.project_name}
                      to={`/projects/${encodeURIComponent(p.project_id)}`}
                    >
                      {p.project_name.split('/').pop() || p.project_name}
                    </Link>
                    <div className="text-xs text-[var(--text-tertiary)] truncate max-w-[12rem] sm:max-w-xs mt-0.5" title={p.project_path || p.project_id}>
                      {p.project_path || p.project_id}
                    </div>
                  </td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">{p.total_sessions}</td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">{formatTokens(p.usage.total_tokens)}</td>
                  <td className="px-4 sm:px-6 py-4 text-right text-[var(--text-secondary)]">{p.total_interactions}</td>
                  <td className="px-4 sm:px-6 py-4 text-right font-mono text-[var(--text-primary)]">{p.cost_usd ? formatUsd(p.cost_usd) : '-'}</td>
                  <td className="px-4 sm:px-6 py-4">
                    <div className="flex flex-wrap gap-1.5">
                      {(p.sources ?? ['self']).map((src) => (
                        <Badge key={src} variant="primary" title={src}>
                          {src === 'self' || src === 'local' ? 'This Server' : src}
                        </Badge>
                      ))}
                    </div>
                  </td>
                </tr>
              ))}
              {(data.projects ?? []).length === 0 && (
                <tr>
                  <td colSpan={6} className="px-4 sm:px-6 py-12 text-center text-[var(--text-tertiary)]">No project usage found in this period.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
