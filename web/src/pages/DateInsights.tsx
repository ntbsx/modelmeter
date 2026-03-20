import { useMemo, useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { CalendarDays, LayoutGrid, FolderOpen, ChevronDown } from 'lucide-react'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { DateInsightsResponse, ModelUsage, ProjectModelUsage } from '../types'
import { useSourceScope } from '../hooks/useSourceScope'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { PageHeader } from '../components/DataTable'
import DatePicker from '../components/DatePicker'

function getTodayDateValue(): string {
  return new Date().toISOString().slice(0, 10)
}

function parseYMD(dateStr: string): { year: number; month: number; day: number } | null {
  const parts = dateStr.split('-')
  if (parts.length !== 3) return null
  const year = parseInt(parts[0], 10)
  const month = parseInt(parts[1], 10) - 1
  const day = parseInt(parts[2], 10)
  if (isNaN(year) || isNaN(month) || isNaN(day)) return null
  return { year, month, day }
}

// Consistent color per provider
const PROVIDER_COLORS = [
  { bg: '#dbeafe', text: '#1e40af' },  // blue
  { bg: '#dcfce7', text: '#166534' },  // green
  { bg: '#f3e8ff', text: '#6b21a8' },  // purple
  { bg: '#fef3c7', text: '#92400e' },  // amber
  { bg: '#ffe4e6', text: '#9f1239' },  // rose
  { bg: '#e0f2fe', text: '#075985' },  // sky
  { bg: '#f0fdf4', text: '#14532d' },  // emerald
  { bg: '#fdf4ff', text: '#7e22ce' },  // violet
]

function providerColor(index: number) {
  return PROVIDER_COLORS[index % PROVIDER_COLORS.length]
}

type Tab = 'providers' | 'projects'

export default function DateInsights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { sourceScope } = useSourceScope()
  const selectedDay = searchParams.get('day') ?? getTodayDateValue()
  const timezoneOffsetMinutes = -new Date().getTimezoneOffset()

  const [showPicker, setShowPicker] = useState(false)
  const [activeTab, setActiveTab] = useState<Tab>('providers')
  const [expandedProviders, setExpandedProviders] = useState<Set<string>>(new Set())
  const [expandedProjects, setExpandedProjects] = useState<Set<string>>(new Set())
  const pickerRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const { data, isLoading, error } = useQuery<DateInsightsResponse>({
    queryKey: ['date-insights', selectedDay, timezoneOffsetMinutes, sourceScope],
    queryFn: () =>
      fetchApi('/date-insights', {
        day: selectedDay,
        timezone_offset_minutes: timezoneOffsetMinutes,
        source_scope: sourceScope,
      }),
  })

  const formattedDay = useMemo(() => {
    const parsed = parseYMD(selectedDay)
    if (!parsed) return selectedDay
    const d = new Date(parsed.year, parsed.month, parsed.day)
    return d.toLocaleDateString('en-US', {
      weekday: 'short',
      month: 'short',
      day: 'numeric',
      year: 'numeric',
    })
  }, [selectedDay])

  const models = useMemo<ModelUsage[]>(() => data?.models ?? [], [data?.models])
  const projectModels = useMemo<ProjectModelUsage[]>(() => data?.project_models ?? [], [data?.project_models])

  const totals = useMemo(() => {
    if (!data) return null
    const costValue = typeof data.cost_usd === 'number' ? formatUsd(data.cost_usd) : 'N/A'
    return [
      { label: 'Total Tokens', value: formatTokens(data.usage.total_tokens) },
      { label: 'Interactions', value: data.total_interactions.toLocaleString() },
      { label: 'Sessions', value: data.total_sessions.toLocaleString() },
      { label: 'Cost', value: costValue },
    ]
  }, [data])

  // Build provider groups with color assignments
  const providerColorMap = useMemo(() => {
    const map = new Map<string, number>()
    const allProviders = [
      ...new Set([
        ...models.map((m) => m.provider ?? 'unknown'),
        ...projectModels.map((pm) => pm.provider ?? 'unknown'),
      ]),
    ]
    allProviders.forEach((p, i) => map.set(p, i))
    return map
  }, [models, projectModels])

  const providerGroups = useMemo(() => {
    const map = new Map<string, ModelUsage[]>()
    for (const model of models) {
      const p = model.provider ?? 'unknown'
      if (!map.has(p)) map.set(p, [])
      map.get(p)!.push(model)
    }
    const sorted = [...map.entries()].sort(([, a], [, b]) => {
      const aTokens = a.reduce((s, m) => s + m.usage.total_tokens, 0)
      const bTokens = b.reduce((s, m) => s + m.usage.total_tokens, 0)
      return bTokens - aTokens
    })
    return sorted.map(([provider, providerModels]) => ({
      provider,
      color: providerColor(providerColorMap.get(provider) ?? 0),
      models: providerModels,
    }))
  }, [models, providerColorMap])

  // Dominant provider color per project
  const projectDominantColor = useMemo(() => {
    const map = new Map<string, { provider: string; colorIdx: number }>()
    for (const pm of projectModels) {
      const p = pm.provider ?? 'unknown'
      const colorIdx = providerColorMap.get(p) ?? 0
      if (!map.has(pm.project_id)) {
        map.set(pm.project_id, { provider: p, colorIdx })
      }
    }
    return map
  }, [projectModels, providerColorMap])

  const handleDayChange = (date: string) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev)
      params.set('day', date)
      return params
    })
    setShowPicker(false)
  }

  const toggleProviderExpanded = (provider: string) => {
    setExpandedProviders((prev) => {
      const next = new Set(prev)
      if (next.has(provider)) next.delete(provider)
      else next.add(provider)
      return next
    })
  }

  const toggleProjectExpanded = (projectId: string) => {
    setExpandedProjects((prev) => {
      const next = new Set(prev)
      if (next.has(projectId)) next.delete(projectId)
      else next.add(projectId)
      return next
    })
  }

  if (isLoading) {
    return <PageLoading title="Date Insights" subtitle="Loading one-day analytics" cards={4} />
  }

  if (error) {
    const body = (error as { data?: { detail?: string } })?.data
    const detail = body?.detail
    const isFederationError =
      detail != null && typeof detail === 'string' && detail.toLowerCase().includes('federated')
    return (
      <PageErrorState
        title={isFederationError ? 'Date insights not available for All Sources' : 'Unable to load date insights'}
        description={
          isFederationError
            ? 'Date insights are currently only available for local source. Switch to "This Server" scope to view date insights.'
            : 'We could not load one-day analytics right now. Try another date or refresh the page.'
        }
      />
    )
  }

  if (!data) {
    return (
      <PageErrorState
        title="Unable to load date insights"
        description="We could not load one-day analytics right now. Try another date or refresh the page."
      />
    )
  }

  const projectList = data.projects ?? []

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <PageHeader
        title="Date Insights"
        description="One-day breakdown across models, providers, and projects"
        actions={
          <div className="relative" ref={pickerRef}>
            <button
              type="button"
              onClick={() => setShowPicker((v) => !v)}
              className="ds-btn-secondary text-sm"
            >
              <CalendarDays className="w-4 h-4" aria-hidden="true" />
              <span>{formattedDay}</span>
            </button>
            {showPicker && (
              <div className="absolute top-full right-0 mt-2 z-50">
                <DatePicker value={selectedDay} onChange={handleDayChange} maxDate={getTodayDateValue()} />
              </div>
            )}
          </div>
        }
      />

      {/* KPI cards */}
      <section className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {totals?.map((item, i) => (
          <div
            key={item.label}
            className="ds-surface p-5 animate-slide-up"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            <p className="ds-text-label-uppercase">{item.label}</p>
            <p className="ds-text-metric mt-1">{item.value}</p>
          </div>
        ))}
      </section>

      {/* Tab switcher — segmented control */}
      <div className="flex items-center gap-1">
        <div className="ds-surface px-1 py-1 rounded-lg flex items-center gap-0.5">
          <button
            type="button"
            onClick={() => setActiveTab('providers')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-150 ${
              activeTab === 'providers'
                ? 'bg-[var(--surface-tertiary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            Providers
            <span
              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                activeTab === 'providers'
                  ? 'bg-[var(--accent-primary)] text-white'
                  : 'bg-[var(--surface-tertiary)] text-[var(--text-tertiary)]'
              }`}
            >
              {providerGroups.length}
            </span>
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('projects')}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-md text-sm font-medium transition-all duration-150 ${
              activeTab === 'projects'
                ? 'bg-[var(--surface-tertiary)] text-[var(--text-primary)] shadow-sm'
                : 'text-[var(--text-tertiary)] hover:text-[var(--text-secondary)]'
            }`}
          >
            <FolderOpen className="w-3.5 h-3.5" />
            Projects
            <span
              className={`text-[10px] font-semibold px-1.5 py-0.5 rounded-full ${
                activeTab === 'projects'
                  ? 'bg-[var(--accent-primary)] text-white'
                  : 'bg-[var(--surface-tertiary)] text-[var(--text-tertiary)]'
              }`}
            >
              {projectList.length}
            </span>
          </button>
        </div>
      </div>

      {/* Provider cards */}
      {activeTab === 'providers' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {providerGroups.length === 0 ? (
            <div className="ds-surface flex flex-col items-center justify-center py-16 gap-3 text-center lg:col-span-2">
              <div className="w-10 h-10 rounded-full bg-[var(--surface-tertiary)] flex items-center justify-center">
                <LayoutGrid className="w-5 h-5 text-[var(--text-tertiary)]" />
              </div>
              <div>
                <p className="ds-text-body font-medium text-[var(--text-secondary)]">No provider usage for this date</p>
                <p className="ds-text-muted mt-0.5">Active models will appear here</p>
              </div>
            </div>
          ) : (
            providerGroups.map(({ provider, color, models: pModels }, gi) => (
              <div
                key={provider}
                className="ds-surface flex flex-col p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-default animate-slide-up"
                style={{
                  borderTop: `3px solid ${color.text}`,
                  animationDelay: `${Math.min(gi, 4) * 60}ms`,
                }}
              >
                {/* Provider header */}
                <div className="flex items-center justify-between mb-3">
                  <div className="flex items-center gap-2">
                    <span
                      className="inline-block px-2 py-0.5 text-xs font-semibold rounded-full"
                      style={{ backgroundColor: color.bg, color: color.text }}
                    >
                      {provider}
                    </span>
                  </div>
                  <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">
                    {pModels.length} model{pModels.length !== 1 ? 's' : ''}
                  </span>
                </div>

                {/* Model breakdown */}
                {pModels.length > 0 ? (
                  <div className="flex flex-col gap-0.5 flex-1">
                    {(expandedProviders.has(provider)
                      ? pModels
                      : pModels.slice(0, 3)
                    ).map((model) => (
                      <div
                        key={model.model_id}
                        className="flex items-center justify-between gap-3 py-2 px-2.5 rounded-md hover:bg-[var(--surface-tertiary)]/50 transition-colors duration-100 group"
                      >
                        <span
                          className="ds-text-body text-[var(--text-secondary)] truncate text-sm font-medium"
                          title={model.model_id}
                        >
                          {model.model_id.split('/').pop() || model.model_id}
                        </span>
                        <div className="flex items-center gap-3 flex-shrink-0">
                          {model.total_interactions > 0 && (
                            <span className="text-[var(--text-tertiary)] text-xs tabular-nums hidden sm:inline">
                              {model.total_interactions.toLocaleString()} req
                            </span>
                          )}
                          <span className="ds-text-tabular font-semibold text-[var(--text-primary)] tabular-nums text-sm">
                            {formatTokens(model.usage.total_tokens)}
                          </span>
                          {typeof model.cost_usd === 'number' ? (
                            <span className="text-[var(--color-success)] font-semibold tabular-nums text-xs min-w-[3.5rem] text-right">
                              {formatUsd(model.cost_usd)}
                            </span>
                          ) : null}
                        </div>
                      </div>
                    ))}
                    {pModels.length > 3 && (
                      <button
                        type="button"
                        onClick={() => toggleProviderExpanded(provider)}
                        className="flex items-center justify-center gap-1 py-1.5 mt-1 text-xs text-[var(--text-tertiary)] hover:text-[var(--accent-primary)] transition-colors duration-100 cursor-pointer rounded-md hover:bg-[var(--surface-tertiary)]/40"
                      >
                        <ChevronDown
                          className={`w-3.5 h-3.5 transition-transform duration-200 ${expandedProviders.has(provider) ? 'rotate-180' : ''}`}
                        />
                        {expandedProviders.has(provider)
                          ? 'Show less'
                          : `${pModels.length - 3} more`}
                      </button>
                    )}
                  </div>
                ) : null}

                {/* Provider totals */}
                <div className="flex items-center justify-between pt-3 mt-auto border-t border-[var(--border-subtle)]">
                  <div className="flex flex-col gap-0.5">
                    <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Tokens</span>
                    <span className="ds-text-tabular font-bold tabular-nums">
                      {formatTokens(pModels.reduce((s, m) => s + m.usage.total_tokens, 0))}
                    </span>
                  </div>
                  {pModels.some((m) => typeof m.cost_usd === 'number') && (
                    <div className="flex flex-col gap-0.5 items-end">
                      <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Cost</span>
                      <span className="ds-text-tabular font-bold text-[var(--color-success)] tabular-nums">
                        {formatUsd(pModels.reduce((s, m) => s + (m.cost_usd ?? 0), 0))}
                      </span>
                    </div>
                  )}
                  {pModels.some((m) => m.total_interactions > 0) && (
                    <div className="flex flex-col gap-0.5 items-end">
                      <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Requests</span>
                      <span className="ds-text-tabular font-bold tabular-nums">
                        {pModels.reduce((s, m) => s + m.total_interactions, 0).toLocaleString()}
                      </span>
                    </div>
                  )}
                </div>
              </div>
            ))
          )}
        </div>
      )}

      {/* Project cards */}
      {activeTab === 'projects' && (
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
          {projectList.length === 0 ? (
            <div className="ds-surface flex flex-col items-center justify-center py-16 gap-3 text-center lg:col-span-2">
              <div className="w-10 h-10 rounded-full bg-[var(--surface-tertiary)] flex items-center justify-center">
                <FolderOpen className="w-5 h-5 text-[var(--text-tertiary)]" />
              </div>
              <div>
                <p className="ds-text-body font-medium text-[var(--text-secondary)]">No project usage for this date</p>
                <p className="ds-text-muted mt-0.5">Projects with active sessions will appear here</p>
              </div>
            </div>
          ) : (
            projectList.map((project, i) => {
              const dominant = projectDominantColor.get(project.project_id)
              const dominantColor = dominant
                ? PROVIDER_COLORS[dominant.colorIdx % PROVIDER_COLORS.length]
                : PROVIDER_COLORS[i % PROVIDER_COLORS.length]
              const projectPmModels = projectModels.filter(
                (pm) => pm.project_id === project.project_id,
              )
              return (
                <div
                  key={project.project_id}
                  className="ds-surface flex flex-col p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md cursor-default animate-slide-up"
                  style={{
                    borderTop: `3px solid ${dominantColor.text}`,
                    animationDelay: `${Math.min(i, 4) * 60}ms`,
                  }}
                >
                  {/* Project header */}
                  <div className="flex flex-col gap-0.5 mb-3">
                    <span
                      className="ds-text-subheading font-semibold truncate"
                      title={project.project_name}
                    >
                      {project.project_name.split('/').pop() || project.project_name}
                    </span>
                    <span
                      className="ds-text-mono text-xs text-[var(--text-tertiary)] truncate"
                      title={project.project_path ?? project.project_id}
                    >
                      {project.project_path ?? project.project_id}
                    </span>
                  </div>

                  {/* Model breakdown */}
                  {projectPmModels.length > 0 ? (
                    <div className="flex flex-col gap-0.5 flex-1">
                      {(expandedProjects.has(project.project_id)
                        ? projectPmModels
                        : projectPmModels.slice(0, 3)
                      ).map((pm) => {
                        const pColor = providerColor(providerColorMap.get(pm.provider ?? 'unknown') ?? 0)
                        return (
                          <div
                            key={pm.model_id}
                            className="flex items-center justify-between gap-3 py-2 px-2.5 rounded-md hover:bg-[var(--surface-tertiary)]/50 transition-colors duration-100 group"
                          >
                            <div className="flex items-center gap-2 min-w-0 flex-1">
                              <span
                                className="inline-block px-1.5 py-0.5 text-xs font-semibold rounded flex-shrink-0"
                                style={{ backgroundColor: pColor.bg, color: pColor.text }}
                              >
                                {pm.provider ?? '?'}
                              </span>
                              <span
                                className="ds-text-body text-[var(--text-secondary)] truncate text-sm font-medium"
                                title={pm.model_id}
                              >
                                {pm.model_id.split('/').pop() || pm.model_id}
                              </span>
                            </div>
                            <div className="flex items-center gap-3 flex-shrink-0">
                              <span className="ds-text-tabular font-semibold text-[var(--text-primary)] tabular-nums text-sm">
                                {formatTokens(pm.usage.total_tokens)}
                              </span>
                              {typeof pm.cost_usd === 'number' ? (
                                <span className="text-[var(--color-success)] font-semibold tabular-nums text-xs min-w-[3.5rem] text-right">
                                  {formatUsd(pm.cost_usd)}
                                </span>
                              ) : null}
                            </div>
                          </div>
                        )
                      })}
                      {projectPmModels.length > 3 && (
                        <button
                          type="button"
                          onClick={() => toggleProjectExpanded(project.project_id)}
                          className="flex items-center justify-center gap-1 py-1.5 mt-1 text-xs text-[var(--text-tertiary)] hover:text-[var(--accent-primary)] transition-colors duration-100 cursor-pointer rounded-md hover:bg-[var(--surface-tertiary)]/40"
                        >
                          <ChevronDown
                            className={`w-3.5 h-3.5 transition-transform duration-200 ${expandedProjects.has(project.project_id) ? 'rotate-180' : ''}`}
                          />
                          {expandedProjects.has(project.project_id)
                            ? 'Show less'
                            : `${projectPmModels.length - 3} more`}
                        </button>
                      )}
                    </div>
                  ) : (
                    <div className="flex-1 flex items-center justify-center py-4">
                      <p className="ds-text-muted text-sm">No model data available</p>
                    </div>
                  )}

                  {/* Project totals */}
                  <div className="flex items-center justify-between pt-3 mt-auto border-t border-[var(--border-subtle)]">
                    <div className="flex flex-col gap-0.5">
                      <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Tokens</span>
                      <span className="ds-text-tabular font-bold tabular-nums">
                        {formatTokens(project.usage.total_tokens)}
                      </span>
                    </div>
                    {typeof project.cost_usd === 'number' ? (
                      <div className="flex flex-col gap-0.5 items-end">
                        <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Cost</span>
                        <span className="ds-text-tabular font-bold text-[var(--color-success)] tabular-nums">
                          {formatUsd(project.cost_usd)}
                        </span>
                      </div>
                    ) : null}
                    {project.total_interactions > 0 && (
                      <div className="flex flex-col gap-0.5 items-end">
                        <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Requests</span>
                        <span className="ds-text-tabular font-bold tabular-nums">
                          {project.total_interactions.toLocaleString()}
                        </span>
                      </div>
                    )}
                  </div>
                </div>
              )
            })
          )}
        </div>
      )}
    </div>
  )
}
