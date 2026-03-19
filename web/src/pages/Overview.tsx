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
import { formatTokens, formatUsd } from '../lib/utils'
import type { DailyResponse, SummaryResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { StatCard } from '../components/ui'
import { PageHeader, StatGrid, SectionHeader } from '../components/DataTable'
import { useChartColors } from '../components/useChartColors'

export default function Overview() {
  const { days } = useDaysFilter()
  const [showTokens, setShowTokens] = useState(true)
  const [showSessions, setShowSessions] = useState(true)
  const [showCost, setShowCost] = useState(true)
  const timezoneOffsetMinutes = -new Date().getTimezoneOffset()
  const { sourceScope } = useSourceScope()
  const chartColors = useChartColors()

  const { data: summary, isLoading: loadingSummary } = useQuery<SummaryResponse>({
    queryKey: ['summary', days, sourceScope],
    queryFn: () => fetchApi('/summary', { days, source_scope: sourceScope })
  })

  const { data: daily, isLoading: loadingDaily } = useQuery<DailyResponse>({
    queryKey: ['daily', days, sourceScope],
    queryFn: () =>
      fetchApi('/daily', {
        days,
        timezone_offset_minutes: timezoneOffsetMinutes,
        source_scope: sourceScope,
      })
  })

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

  const hasMultipleDays = chartData.length > 1
  const hasEnoughData = chartData.length >= 3
  const showTrendChart = hasEnoughData
  const showComparisonView = hasMultipleDays && !hasEnoughData
  const showSingleDay = chartData.length === 1

  const latestDay = chartData[chartData.length - 1]
  const previousDay = chartData.length >= 2 ? chartData[chartData.length - 2] : null

  const getDelta = (current: number, previous: number) => {
    if (!previous || previous === 0) return null
    const diff = current - previous
    const percent = ((diff / previous) * 100).toFixed(1)
    return { diff, percent, isPositive: diff >= 0 }
  }

  const tokensDelta = latestDay && previousDay ? getDelta(latestDay.tokens, previousDay.tokens) : null
  const costDelta = latestDay && previousDay ? getDelta(latestDay.cost, previousDay.cost) : null
  const sessionsDelta = latestDay && previousDay ? getDelta(latestDay.sessions, previousDay.sessions) : null

  const tooltipContentStyle = {
    backgroundColor: chartColors.tooltip.background,
    borderColor: chartColors.tooltip.border,
    color: chartColors.tooltip.text,
  }
  const avgDailyTokens =
    chartData.length > 0
      ? Math.round(chartData.reduce((sum, point) => sum + point.tokens, 0) / chartData.length)
      : 0

  const avgDailyCost =
    chartData.length > 0
      ? chartData.reduce((sum, point) => sum + (point.cost || 0), 0) / chartData.length
      : 0

  const avgDailySessions =
    chartData.length > 0
      ? Math.round(chartData.reduce((sum, point) => sum + point.sessions, 0) / chartData.length)
      : 0

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto space-y-10 sm:space-y-12 lg:space-y-16">
      <PageHeader
        title="Overview"
        description={`${days === 1 ? 'Last 24 hours' : `Last ${days} days`} of OpenCode usage`}
      />

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
            delay={30}
            accent="blue"
            icon={<Zap className="w-5 h-5" />}
          />
          <StatCard 
            label="Cache Read" 
            value={formatTokens(summary.usage.cache_read_tokens)} 
            delay={60}
            accent="amber"
            icon={<Database className="w-5 h-5" />}
          />
          <StatCard 
            label="Sessions" 
            value={summary.total_sessions.toString()} 
            delay={90}
            accent="purple"
            icon={<Activity className="w-5 h-5" />}
          />
        </StatGrid>
      </section>

      <section className="ds-surface overflow-hidden content-auto">
        <div className="p-5 sm:p-8 border-b border-[var(--border-subtle)]">
          <SectionHeader
            title="Usage Trend"
            description="Tokens, sessions, and spend across the selected window"
            accent
            actions={
              showTrendChart || showComparisonView ? (
                <div className="flex flex-wrap items-center gap-1 shrink-0">
                  {showTrendChart && (
                    <>
                      <span className="text-[10px] text-[var(--text-tertiary)] uppercase tracking-wider mr-2 opacity-60">Show:</span>
                      <button
                        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all cursor-pointer min-h-[44px] focus-ring ${
                          showSessions
                            ? 'text-[var(--chart-sessions)]'
                            : 'text-[var(--text-tertiary)] opacity-40'
                        }`}
                        onClick={() => setShowSessions((value) => !value)}
                        type="button"
                        title={showSessions ? 'Hide sessions' : 'Show sessions'}
                      >
                        <span className="w-2 h-1.5 rounded-sm" style={{ backgroundColor: showSessions ? 'currentColor' : 'var(--border-default)' }} />
                        <span className="text-xs">Sessions</span>
                      </button>
                      <button
                        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all cursor-pointer min-h-[44px] focus-ring ${
                          showTokens
                            ? 'text-[var(--chart-tokens)]'
                            : 'text-[var(--text-tertiary)] opacity-40'
                        }`}
                        onClick={() => setShowTokens((value) => !value)}
                        type="button"
                        title={showTokens ? 'Hide tokens' : 'Show tokens'}
                      >
                        <span className="w-3 h-0.5 rounded-full" style={{ backgroundColor: showTokens ? 'currentColor' : 'var(--border-default)' }} />
                        <span className="text-xs">Tokens</span>
                      </button>
                      <button
                        className={`flex items-center gap-1.5 px-3 py-2 rounded-lg transition-all cursor-pointer min-h-[44px] focus-ring ${
                          showCost
                            ? 'text-[var(--chart-cost)]'
                            : 'text-[var(--text-tertiary)] opacity-40'
                        }`}
                        onClick={() => setShowCost((value) => !value)}
                        type="button"
                        title={showCost ? 'Hide cost' : 'Show cost'}
                      >
                        <span className="w-3 h-0.5 rounded-full border-dashed border" style={{ borderColor: showCost ? 'currentColor' : 'var(--border-default)', backgroundColor: 'transparent' }} />
                        <span className="text-xs">Cost</span>
                      </button>
                    </>
                  )}
                  {showComparisonView && (
                    <span className="text-xs text-[var(--text-tertiary)]">Day-over-day comparison</span>
                  )}
                </div>
              ) : null
            }
          />
          {avgDailyTokens > 0 && (
            <div className="mt-6 pt-4 border-t border-[var(--border-subtle)]">
              <div className="flex flex-wrap gap-x-6 gap-y-2">
                <div className="flex items-center gap-2 ds-text-muted">
                  <span className="font-semibold text-[var(--text-primary)] ds-text-tabular">{formatTokens(avgDailyTokens)}</span>
                  <span className="ds-text-label-uppercase">avg daily tokens</span>
                </div>
                <div className="flex items-center gap-2 ds-text-muted">
                  <span className="font-semibold text-[var(--text-primary)] ds-text-tabular">{formatUsd(avgDailyCost)}</span>
                  <span className="ds-text-label-uppercase">avg daily cost</span>
                </div>
                <div className="flex items-center gap-2 ds-text-muted">
                  <span className="font-semibold text-[var(--text-primary)] ds-text-tabular">{avgDailySessions}</span>
                  <span className="ds-text-label-uppercase">avg daily sessions</span>
                </div>
              </div>
            </div>
          )}
        </div>
        <div className="space-y-4">
          {showTrendChart ? (
            <>
              <div className="h-72 p-4 sm:p-6 pt-2 sm:pt-4">
                <ResponsiveContainer width="100%" height="100%">
                  <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 4, bottom: 0 }}>
                    <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartColors.grid} />
                    <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: chartColors.axis }} />
                    <YAxis
                      yAxisId="left"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: chartColors.axis }}
                      hide={!showTokens}
                      tickFormatter={(value: number | string) => formatTokens(Number(value))}
                      width={56}
                    />
                    <YAxis
                      yAxisId="right"
                      orientation="right"
                      axisLine={false}
                      tickLine={false}
                      tick={{ fill: chartColors.axis }}
                      hide={!showCost}
                      tickFormatter={(value: number | string) => formatUsd(Number(value))}
                      width={56}
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
                        return [formatTokens(numericValue), 'Tokens']
                      }}
                    />
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
              {showSessions && (
                <div className="h-44 p-4 sm:px-6 pb-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartColors.grid} />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: chartColors.axis }} />
                      <YAxis
                        yAxisId="left"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: chartColors.axis }}
                        tickFormatter={(value: number | string) => Number(value).toLocaleString()}
                        width={48}
                      />
                      <Tooltip
                        contentStyle={tooltipContentStyle}
                        formatter={(
                          value: number | string | readonly (number | string)[] | undefined
                        ) => {
                          const baseValue = Array.isArray(value) ? value[0] : value
                          const numericValue = Number(baseValue ?? 0)
                          return [numericValue.toLocaleString(), 'Sessions']
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="sessions"
                        name="Sessions"
                        fill={chartColors.sessions.fill}
                        radius={[2, 2, 0, 0]}
                        maxBarSize={20}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </>
          ) : showComparisonView ? (
            <div className="space-y-4">
              <div className="p-4 sm:p-6">
                <div className="hidden sm:grid sm:grid-cols-4 gap-2 sm:gap-4">
                  <div />
                  <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider text-center">
                    {previousDay?.date}
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider text-center">
                    {latestDay?.date}
                  </div>
                  <div className="text-xs text-[var(--text-tertiary)] uppercase tracking-wider text-center">
                    Change
                  </div>
                  
                  <div className="text-sm text-[var(--text-tertiary)]">Tokens</div>
                  <div className="text-xl font-semibold text-[var(--text-primary)] ds-text-tabular text-right">
                    {formatTokens(previousDay?.tokens ?? 0)}
                  </div>
                  <div className="text-xl font-semibold text-[var(--text-primary)] ds-text-tabular text-right">
                    {formatTokens(latestDay?.tokens ?? 0)}
                  </div>
                  <div className={`text-sm font-medium ds-text-tabular text-right ${tokensDelta ? (tokensDelta.isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]') : 'text-[var(--text-tertiary)]'}`}>
                    {tokensDelta ? `${tokensDelta.isPositive ? '+' : ''}${tokensDelta.percent}%` : '—'}
                  </div>

                  <div className="text-sm text-[var(--text-tertiary)]">Cost</div>
                  <div className="text-lg text-[var(--text-secondary)] ds-text-tabular text-right">
                    {formatUsd(previousDay?.cost ?? 0)}
                  </div>
                  <div className="text-lg text-[var(--text-secondary)] ds-text-tabular text-right">
                    {formatUsd(latestDay?.cost ?? 0)}
                  </div>
                  <div className={`text-sm font-medium ds-text-tabular text-right ${costDelta ? (costDelta.isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]') : 'text-[var(--text-tertiary)]'}`}>
                    {costDelta ? `${costDelta.isPositive ? '+' : ''}${costDelta.percent}%` : '—'}
                  </div>

                  <div className="text-sm text-[var(--text-tertiary)]">Sessions</div>
                  <div className="text-lg text-[var(--text-secondary)] ds-text-tabular text-right">
                    {previousDay?.sessions ?? 0}
                  </div>
                  <div className="text-lg text-[var(--text-secondary)] ds-text-tabular text-right">
                    {latestDay?.sessions ?? 0}
                  </div>
                  <div className={`text-sm font-medium ds-text-tabular text-right ${sessionsDelta ? (sessionsDelta.isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]') : 'text-[var(--text-tertiary)]'}`}>
                    {sessionsDelta?.diff !== undefined ? `${sessionsDelta.isPositive ? '+' : ''}${sessionsDelta.diff}` : '—'}
                    {sessionsDelta && sessionsDelta.diff !== undefined && (
                      <span className="text-xs opacity-60 ml-1">({sessionsDelta.percent}%)</span>
                    )}
                  </div>
                </div>
                <div className="sm:hidden space-y-4">
                  <div className="flex justify-between items-center">
                    <span className="text-sm font-medium text-[var(--text-primary)]">Tokens</span>
                    <span className={`text-sm font-medium ${tokensDelta ? (tokensDelta.isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]') : 'text-[var(--text-tertiary)]'}`}>
                      {tokensDelta ? `${tokensDelta.isPositive ? '+' : ''}${tokensDelta.percent}%` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-tertiary)]">{previousDay?.date}: {formatTokens(previousDay?.tokens ?? 0)}</span>
                    <span className="text-[var(--text-tertiary)]">{latestDay?.date}: {formatTokens(latestDay?.tokens ?? 0)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center pt-2 border-t border-[var(--border-subtle)]">
                    <span className="text-sm font-medium text-[var(--text-primary)]">Cost</span>
                    <span className={`text-sm font-medium ${costDelta ? (costDelta.isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]') : 'text-[var(--text-tertiary)]'}`}>
                      {costDelta ? `${costDelta.isPositive ? '+' : ''}${costDelta.percent}%` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-tertiary)]">{previousDay?.date}: {formatUsd(previousDay?.cost ?? 0)}</span>
                    <span className="text-[var(--text-tertiary)]">{latestDay?.date}: {formatUsd(latestDay?.cost ?? 0)}</span>
                  </div>
                  
                  <div className="flex justify-between items-center pt-2 border-t border-[var(--border-subtle)]">
                    <span className="text-sm font-medium text-[var(--text-primary)]">Sessions</span>
                    <span className={`text-sm font-medium ${sessionsDelta ? (sessionsDelta.isPositive ? 'text-[var(--color-success)]' : 'text-[var(--color-error)]') : 'text-[var(--text-tertiary)]'}`}>
                      {sessionsDelta?.diff !== undefined ? `${sessionsDelta.isPositive ? '+' : ''}${sessionsDelta.diff}` : '—'}
                    </span>
                  </div>
                  <div className="flex justify-between text-sm">
                    <span className="text-[var(--text-tertiary)]">{previousDay?.date}: {previousDay?.sessions ?? 0}</span>
                    <span className="text-[var(--text-tertiary)]">{latestDay?.date}: {latestDay?.sessions ?? 0}</span>
                  </div>
                </div>
              </div>
              {showSessions && (
                <div className="h-44 p-4 sm:px-6 pb-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartColors.grid} />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: chartColors.axis }} />
                      <YAxis
                        yAxisId="left"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: chartColors.axis }}
                        tickFormatter={(value: number | string) => Number(value).toLocaleString()}
                        width={48}
                      />
                      <Tooltip
                        contentStyle={tooltipContentStyle}
                        formatter={(
                          value: number | string | readonly (number | string)[] | undefined
                        ) => {
                          const baseValue = Array.isArray(value) ? value[0] : value
                          const numericValue = Number(baseValue ?? 0)
                          return [numericValue.toLocaleString(), 'Sessions']
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="sessions"
                        name="Sessions"
                        fill={chartColors.sessions.fill}
                        radius={[2, 2, 0, 0]}
                        maxBarSize={40}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          ) : showSingleDay ? (
            <div className="space-y-4">
              <div className="p-4 sm:p-6 text-center text-[var(--text-tertiary)]">
                Showing data for {latestDay?.date}
              </div>
              {showSessions && (
                <div className="h-44 p-4 sm:px-6 pb-4">
                  <ResponsiveContainer width="100%" height="100%">
                    <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={chartColors.grid} />
                      <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: chartColors.axis }} />
                      <YAxis
                        yAxisId="left"
                        axisLine={false}
                        tickLine={false}
                        tick={{ fill: chartColors.axis }}
                        tickFormatter={(value: number | string) => Number(value).toLocaleString()}
                        width={48}
                      />
                      <Tooltip
                        contentStyle={tooltipContentStyle}
                        formatter={(
                          value: number | string | readonly (number | string)[] | undefined
                        ) => {
                          const baseValue = Array.isArray(value) ? value[0] : value
                          const numericValue = Number(baseValue ?? 0)
                          return [numericValue.toLocaleString(), 'Sessions']
                        }}
                      />
                      <Bar
                        yAxisId="left"
                        dataKey="sessions"
                        name="Sessions"
                        fill={chartColors.sessions.fill}
                        radius={[2, 2, 0, 0]}
                        maxBarSize={40}
                      />
                    </ComposedChart>
                  </ResponsiveContainer>
                </div>
              )}
            </div>
          ) : (
            <div className="p-4 sm:p-6 text-center text-[var(--text-tertiary)]">
              Select a longer date range to view trends
            </div>
          )}
        </div>
      </section>
    </div>
  )
}
