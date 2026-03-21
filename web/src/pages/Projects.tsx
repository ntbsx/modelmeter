import { useRef, useEffect, useState, useMemo } from 'react'
import { Link } from 'react-router-dom'
import {
  Bar,
  BarChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { formatTokens, formatUsd } from '../lib/utils'
import type { ProjectUsage } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { PageHeader } from '../components/DataTable'
import { Badge } from '../components/ui'
import DaysFilterPicker from '../components/DaysFilterPicker'
import { useChartColors } from '../components/useChartColors'
import { useProjectList } from '../hooks/useEntityList'

export default function Projects() {
  const { days } = useDaysFilter('projects')
  const { sourceScope } = useSourceScope()
  const [chartMetric, setChartMetric] = useState<'tokens' | 'cost'>('tokens')
  const sentinelRef = useRef<HTMLDivElement>(null)
  const colors = useChartColors()

  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useProjectList({ days, sourceScope })

  const allProjects = useMemo(
    () => data?.pages.flatMap((p) => p.projects ?? []) ?? [],
    [data]
  )

  const chartData = useMemo(
    () => allProjects.slice(0, 10).map((p) => ({
      name: (p.project_name.split('/').pop() || p.project_name).slice(0, 24),
      tokens: p.usage.total_tokens,
      cost: p.cost_usd ?? 0,
      fullName: p.project_name,
    })),
    [allProjects]
  )

  useEffect(() => {
    const sentinel = sentinelRef.current
    if (!sentinel || !hasNextPage) return
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting && !isFetchingNextPage) fetchNextPage()
    })
    observer.observe(sentinel)
    return () => observer.disconnect()
  }, [hasNextPage, isFetchingNextPage, fetchNextPage])

  if (isLoading) return <PageLoading title="Projects" subtitle="Loading project usage" cards={3} />
  if (isError || !data) {
    return (
      <PageErrorState
        title="Unable to load projects"
        description="We could not fetch project usage right now. Try refreshing the page."
      />
    )
  }

  const firstPage = data.pages[0]

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <PageHeader
        title="Projects"
        description={`${firstPage.total_projects} project${firstPage.total_projects !== 1 ? 's' : ''} \u00b7 ${days === 1 ? 'last 24 hours' : `last ${days} days`}`}
        actions={<DaysFilterPicker scope="projects" />}
      />

      {chartData.length > 0 && (
        <div className="ds-surface p-4 sm:p-5 mb-6 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
              Project Distribution
            </span>
            <div className="ds-surface px-1 py-1 rounded-lg flex items-center gap-0.5">
              <button
                type="button"
                onClick={() => setChartMetric('tokens')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors focus-ring ${
                  chartMetric === 'tokens'
                    ? 'bg-[var(--accent-primary)] text-white'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Tokens
              </button>
              <button
                type="button"
                onClick={() => setChartMetric('cost')}
                className={`px-3 py-1 rounded-md text-xs font-medium transition-colors focus-ring ${
                  chartMetric === 'cost'
                    ? 'bg-[var(--accent-primary)] text-white'
                    : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Cost
              </button>
            </div>
          </div>
          <ResponsiveContainer width="100%" height={Math.min(40 + chartData.length * 30, 340)}>
            <BarChart
              layout="vertical"
              data={chartData}
              margin={{ top: 0, right: 16, bottom: 0, left: 4 }}
            >
              <CartesianGrid horizontal={false} stroke={colors.grid} strokeDasharray="3 3" />
              <XAxis
                type="number"
                dataKey={chartMetric}
                tickFormatter={chartMetric === 'tokens' ? formatTokens : formatUsd}
                tick={{ fontSize: 11, fill: colors.axis }}
                axisLine={false}
                tickLine={false}
              />
              <YAxis
                type="category"
                dataKey="name"
                width={120}
                tick={{ fontSize: 11, fill: colors.axis }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                formatter={(value: number | string | readonly (number | string)[] | undefined) => {
                  const v = Number(Array.isArray(value) ? value[0] : (value ?? 0))
                  return chartMetric === 'tokens' ? formatTokens(v) : formatUsd(v)
                }}
                labelFormatter={(_label, payload) =>
                  payload?.[0]?.payload?.fullName ?? String(_label ?? '')
                }
                contentStyle={{
                  background: colors.tooltip.background,
                  border: `1px solid ${colors.tooltip.border}`,
                  borderRadius: 6,
                  fontSize: 12,
                }}
                cursor={{ fill: 'var(--surface-tertiary)' }}
              />
              <Bar
                dataKey={chartMetric}
                fill={chartMetric === 'tokens' ? colors.tokens.fill : colors.cost.fill}
                radius={[0, 3, 3, 0]}
              />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}

      {allProjects.length === 0 ? (
        <div className="ds-surface flex flex-col items-center justify-center py-16 gap-3 text-center">
          <p className="font-medium text-[var(--text-secondary)]">No project usage found in this period.</p>
          <p className="text-sm text-[var(--text-tertiary)]">
            Organize your API calls into projects to track usage by project.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {allProjects.map((p, i) => (
            <ProjectCard key={p.project_id} project={p} index={i} />
          ))}
        </div>
      )}

      <div ref={sentinelRef} className="h-4 mt-4" />
      {isFetchingNextPage && (
        <div className="flex justify-center py-6">
          <div className="w-5 h-5 rounded-full border-2 border-[var(--accent-primary)] border-t-transparent animate-spin" />
        </div>
      )}
    </div>
  )
}

function ProjectCard({ project, index }: { project: ProjectUsage; index: number }) {
  const shortName = project.project_name.split('/').pop() || project.project_name
  const sources = project.sources ?? ['self']

  return (
    <Link
      to={`/projects/${encodeURIComponent(project.project_id)}`}
      className="ds-surface focus-ring flex flex-col p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md animate-slide-up"
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="mb-3">
        <div
          className="font-medium text-[var(--text-primary)] truncate text-sm"
          title={project.project_name}
        >
          {shortName}
        </div>
        <div
          className="text-xs text-[var(--text-tertiary)] truncate mt-0.5"
          title={project.project_path ?? project.project_id}
        >
          {project.project_path ?? project.project_id}
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[var(--border-subtle)]">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Sessions
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {project.total_sessions}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Tokens
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {formatTokens(project.usage.total_tokens)}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Cost
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {project.cost_usd != null ? formatUsd(project.cost_usd) : '–'}
          </div>
        </div>
      </div>

      {sources.length > 0 && (
        <div className="flex flex-wrap gap-1.5 mt-3 pt-3 border-t border-[var(--border-subtle)]">
          {sources.map((src) => (
            <Badge key={src} variant="primary" title={src}>
              {src === 'self' || src === 'local' ? 'This Server' : src}
            </Badge>
          ))}
        </div>
      )}
    </Link>
  )
}
