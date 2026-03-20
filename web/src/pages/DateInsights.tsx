import { useMemo, useState, useRef, useEffect } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useSearchParams } from 'react-router-dom'
import { CalendarDays } from 'lucide-react'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { DateInsightsResponse, ModelUsage } from '../types'
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

export default function DateInsights() {
  const [searchParams, setSearchParams] = useSearchParams()
  const { sourceScope } = useSourceScope()
  const selectedDay = searchParams.get('day') ?? getTodayDateValue()
  const timezoneOffsetMinutes = -new Date().getTimezoneOffset()

  const [showPicker, setShowPicker] = useState(false)
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

  const projects = useMemo(() => data?.projects ?? [], [data?.projects])

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

  // Rows for table: first model of each group includes rowSpan, rest don't
  // Each cell index maps directly to the 5 header columns: Provider | Model | Interactions | Tokens | Cost
  const providerModelRows = useMemo(() => {
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
    type Row = { provider: string; rowSpan: number; model: ModelUsage }
    const rows: Row[] = []
    for (const [provider, providerModels] of sorted) {
      for (let i = 0; i < providerModels.length; i++) {
        rows.push({ provider, rowSpan: i === 0 ? providerModels.length : 0, model: providerModels[i] })
      }
    }
    return rows
  }, [models])

  const handleDayChange = (date: string) => {
    setSearchParams((prev) => {
      const params = new URLSearchParams(prev)
      params.set('day', date)
      return params
    })
    setShowPicker(false)
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

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto space-y-8">
      <PageHeader
        title="Date Insights"
        description="Exact one-day breakdown across models, providers, and projects"
        actions={
          <div className="relative" ref={pickerRef}>
            <button
              type="button"
              onClick={() => setShowPicker((v) => !v)}
              className="inline-flex items-center gap-2 rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-1.5 text-sm text-[var(--text-primary)] hover:bg-[var(--surface-tertiary)] transition-colors"
            >
              <CalendarDays className="w-4 h-4 text-[var(--text-secondary)]" aria-hidden="true" />
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

      <section className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        {totals?.map((item) => (
          <div key={item.label} className="ds-surface p-4">
            <p className="text-xs uppercase tracking-wide text-[var(--text-tertiary)]">{item.label}</p>
            <p className="mt-2 text-xl font-semibold text-[var(--text-primary)]">{item.value}</p>
          </div>
        ))}
      </section>

      <section className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <div className="ds-surface overflow-hidden">
          <h2 className="px-4 sm:px-6 py-4 text-sm font-semibold text-[var(--text-secondary)] border-b border-[var(--border-default)]">
            Provider &amp; Model
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  <th className="px-4 sm:px-6 py-3 text-left font-medium text-[var(--text-secondary)]">Provider</th>
                  <th className="px-4 sm:px-6 py-3 text-left font-medium text-[var(--text-secondary)]">Model</th>
                  <th className="px-4 sm:px-6 py-3 text-right font-medium text-[var(--text-secondary)]">Interactions</th>
                  <th className="px-4 sm:px-6 py-3 text-right font-medium text-[var(--text-secondary)]">Tokens</th>
                  <th className="px-4 sm:px-6 py-3 text-right font-medium text-[var(--text-secondary)]">Cost</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {providerModelRows.map(({ provider, rowSpan, model }) => (
                  <tr key={model.model_id} className="hover:bg-[var(--surface-hover)]">
                    {rowSpan > 0 ? (
                      <td
                        rowSpan={rowSpan}
                        className="px-4 sm:px-6 py-3 font-semibold text-[var(--text-primary)] align-top"
                      >
                        {provider}
                      </td>
                    ) : null}
                    <td className="px-4 sm:px-6 py-3 text-[var(--text-secondary)]">{model.model_id}</td>
                    <td className="px-4 sm:px-6 py-3 text-right text-[var(--text-secondary)]">
                      {model.total_interactions}
                    </td>
                    <td className="px-4 sm:px-6 py-3 text-right text-[var(--text-primary)]">
                      {formatTokens(model.usage.total_tokens)}
                    </td>
                    <td className="px-4 sm:px-6 py-3 text-right text-[var(--text-primary)]">
                      {typeof model.cost_usd === 'number' ? formatUsd(model.cost_usd) : '-'}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>

        <div className="ds-surface overflow-hidden">
          <h2 className="px-4 sm:px-6 py-4 text-sm font-semibold text-[var(--text-secondary)] border-b border-[var(--border-default)]">
            Projects
          </h2>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-[var(--border-subtle)]">
                  <th className="px-4 sm:px-6 py-3 text-left font-medium text-[var(--text-secondary)]">Project</th>
                  <th className="px-4 sm:px-6 py-3 text-right font-medium text-[var(--text-secondary)]">Interactions</th>
                  <th className="px-4 sm:px-6 py-3 text-right font-medium text-[var(--text-secondary)]">Tokens</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[var(--border-subtle)]">
                {projects.map((project) => (
                  <tr key={project.project_id}>
                    <td className="px-4 sm:px-6 py-3 text-[var(--text-primary)]">{project.project_name}</td>
                    <td className="px-4 sm:px-6 py-3 text-right text-[var(--text-secondary)]">
                      {project.total_interactions}
                    </td>
                    <td className="px-4 sm:px-6 py-3 text-right text-[var(--text-primary)]">
                      {formatTokens(project.usage.total_tokens)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </section>
    </div>
  )
}
