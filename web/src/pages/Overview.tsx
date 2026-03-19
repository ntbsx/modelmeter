import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import {
  Bar,
  CartesianGrid,
  ComposedChart,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { DollarSign, Zap, Database, Activity } from 'lucide-react'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd, cn } from '../lib/utils'
import type { DailyResponse, SummaryResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { StatCard } from '../components/ui'
import { PageHeader, StatGrid, SectionHeader } from '../components/DataTable'
import { useChartColors } from '../components/useChartColors'
import SourceStatusBanner from '../components/SourceStatusBanner'

export default function Overview() {
  const { days } = useDaysFilter()
  const [showTokens, setShowTokens] = useState(true)
  const [showSessions, setShowSessions] = useState(true)
  const [showCost, setShowCost] = useState(true)
  const timezoneOffsetMinutes = -new Date().getTimezoneOffset()
  const { sourceScope } = useSourceScope()
  const chartColors = useChartColors()

  const { data: summary, isLoading: loadingSummary, isFetching: isRefetchingSummary } = useQuery<SummaryResponse>({
    queryKey: ['summary', days, sourceScope],
    queryFn: () => fetchApi('/summary', { days, source_scope: sourceScope })
  })

  const { data: daily, isLoading: loadingDaily, isFetching: isRefetchingDaily } = useQuery<DailyResponse>({
    queryKey: ['daily', days, sourceScope],
    queryFn: () =>
      fetchApi('/daily', {
        days,
        timezone_offset_minutes: timezoneOffsetMinutes,
        source_scope: sourceScope,
      })
  })

  const isRefetching = isRefetchingSummary || isRefetchingDaily

  if (loadingSummary || loadingDaily) {
    return <PageLoading title="Overview" subtitle="Loading usage metrics" cards={4} />
  }

  if (!summary || !daily) {
    return (
      <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
        <div className="ds-surface p-6 bg-[var(--color-error-muted)] border-[var(--color-error)]">
          <div className="flex items-start gap-3">
            <span className="text-[var(--color-error)]">Unable to load overview</span>
            <div>
              <p className="text-sm text-[var(--color-error-muted-foreground)]">We could not load summary metrics right now. Try refreshing the page.</p>
            </div>
          </div>
        </div>
      </div>
    )
  }

  const chartData = (daily.daily ?? []).map((entry) => {
      const [year, month, day] = entry.day.split('-').map(Number)
      const parsed = new Date(year, (month || 1) - 1, day || 1)
      return {
        date: parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        tokens: entry.usage.total_tokens,
        cost: entry.cost_usd || 0,
        sessions: entry.total_sessions,
      }
    })

  const leftAxisTicks = showTokens || showSessions

  const tooltipContentStyle = {
    backgroundColor: chartColors.tooltip.background,
    borderColor: chartColors.tooltip.border,
    color: chartColors.tooltip.text,
  }
  const avgDailyTokens =
    chartData.length > 0
      ? Math.round(chartData.reduce((sum, point) => sum + point.tokens, 0) / chartData.length)
      : 0

  const hasData = (summary?.usage.total_tokens ?? 0) > 0 || (summary?.total_sessions ?? 0) > 0

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto space-y-10 sm:space-y-12 lg:space-y-16">
      <PageHeader
        title="Overview"
        description={`${days === 1 ? 'Last 24 hours' : `Last ${days} days`} of OpenCode usage`}
      />

      <SourceStatusBanner
        isLoading={loadingSummary || loadingDaily}
        isFetching={isRefetching}
        sourceScope={sourceScope}
        sourcesConsidered={summary?.sources_considered ?? daily?.sources_considered ?? []}
        sourcesSucceeded={summary?.sources_succeeded ?? daily?.sources_succeeded ?? []}
        sourcesFailed={summary?.sources_failed ?? daily?.sources_failed ?? []}
        hasData={hasData}
      />

      <div className={cn('transition-opacity', isRefetching && 'opacity-60')}>
        <section>
          <StatGrid columns={4}>
          <StatCard 
            label="Total Cost" 
            value={summary.cost_usd ? formatUsd(summary.cost_usd) : 'N/A'}
            subtitle={summary.pricing_source ? "via models.dev" : "No pricing data"}
            delay={0}
            accent="green"
            icon={<DollarSign className="w-5 h-5" />}
          />
          <StatCard 
            label="Total Tokens" 
            value={formatTokens(summary.usage.total_tokens)} 
            delay={50}
            accent="blue"
            icon={<Zap className="w-5 h-5" />}
          />
          <StatCard 
            label="Cache Read" 
            value={formatTokens(summary.usage.cache_read_tokens)} 
            delay={100}
            accent="amber"
            icon={<Database className="w-5 h-5" />}
          />
          <StatCard 
            label="Sessions" 
            value={summary.total_sessions.toString()} 
            delay={150}
            accent="purple"
            icon={<Activity className="w-5 h-5" />}
          />
        </StatGrid>
      </section>

      <section className="ds-surface overflow-hidden">
        <div className="p-5 sm:p-8 border-b border-[var(--border-subtle)]">
          <SectionHeader
            title="Usage Trend"
            description="Tokens, sessions, and spend across the selected window"
            accent
            actions={
              <div className="flex flex-wrap gap-2 shrink-0">
                <button
                  className={`px-3 py-1.5 rounded-md border transition-colors ${
                    showSessions
                      ? 'border-[var(--chart-sessions)] bg-[var(--chart-sessions)]/20 text-[var(--text-primary)]'
                    : 'border-[var(--border-default)] text-[var(--text-tertiary)]'
                }`}
                onClick={() => setShowSessions((value) => !value)}
                type="button"
              >
                Sessions
              </button>
              <button
                className={`px-3 py-1.5 rounded-md border transition-colors ${
                  showTokens
                    ? 'border-[var(--chart-tokens)] bg-[var(--chart-tokens)]/20 text-[var(--accent-primary)]'
                    : 'border-[var(--border-default)] text-[var(--text-tertiary)]'
                }`}
                onClick={() => setShowTokens((value) => !value)}
                type="button"
              >
                Tokens
              </button>
              <button
                className={`px-3 py-1.5 rounded-md border transition-colors ${
                  showCost
                    ? 'border-[var(--chart-cost)] bg-[var(--chart-cost)]/20 text-[var(--chart-cost)]'
                    : 'border-[var(--border-default)] text-[var(--text-tertiary)]'
                }`}
                onClick={() => setShowCost((value) => !value)}
                type="button"
              >
                Cost
              </button>
              </div>
            }
          />
          {avgDailyTokens > 0 && (
            <div className="mt-6 pt-4 border-t border-[var(--border-subtle)]">
              <div className="flex items-center gap-2 ds-text-muted">
                <span className="ds-text-label-uppercase">Avg daily tokens</span>
                <span className="font-semibold text-[var(--text-primary)] ds-text-tabular">{formatTokens(avgDailyTokens)}</span>
              </div>
            </div>
          )}
        </div>
        <div className="h-80 p-4 sm:p-6 pt-2 sm:pt-4">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartColors.grid} />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: chartColors.axis }} />
              <YAxis
                yAxisId="left"
                axisLine={false}
                tickLine={false}
                tick={{ fill: chartColors.axis }}
                hide={!leftAxisTicks}
                tickFormatter={(value: number | string) => formatTokens(Number(value))}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                axisLine={false}
                tickLine={false}
                tick={{ fill: chartColors.axis }}
                hide={!showCost}
                tickFormatter={(value: number | string) => formatUsd(Number(value))}
              />
              <Tooltip
                contentStyle={tooltipContentStyle}
                formatter={(
                  value: number | string | readonly (number | string)[] | undefined,
                  name: string | number | undefined
                ) => {
                  const baseValue = Array.isArray(value) ? value[0] : value
                  const numericValue = Number(baseValue ?? 0)
                  const seriesName = String(name ?? '')
                  if (seriesName === 'Cost') {
                    return [formatUsd(numericValue), 'Cost']
                  }
                  if (seriesName === 'Sessions') {
                    return [numericValue.toLocaleString(), 'Sessions']
                  }
                  return [formatTokens(numericValue), 'Tokens']
                }}
              />
              {showSessions ? (
                <Bar
                  yAxisId="left"
                  dataKey="sessions"
                  name="Sessions"
                  fill={chartColors.sessions.fill}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={28}
                />
              ) : null}
              {showTokens ? (
                <Line
                  yAxisId="left"
                  type="monotone"
                  dataKey="tokens"
                  name="Tokens"
                  stroke={chartColors.tokens.stroke}
                  strokeWidth={2.5}
                  dot={{ r: 3, strokeWidth: 0, fill: chartColors.tokens.fill }}
                  activeDot={{ r: 5 }}
                />
              ) : null}
              {showCost ? (
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="cost"
                  name="Cost"
                  stroke={chartColors.cost.stroke}
                  strokeWidth={2}
                  dot={false}
                  strokeDasharray="5 3"
                />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </section>
      </div>
    </div>
  )
}
