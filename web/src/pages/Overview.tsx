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
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { DailyResponse, SummaryResponse } from '../types'
import { useTheme } from '../components/useTheme'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'

const RANGE_OPTIONS = [7, 30, 90] as const

function StatCard({ title, value, subtitle }: { title: string, value: string, subtitle?: string }) {
  return (
    <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
      <div className="text-sm font-medium text-gray-500 dark:text-gray-400 mb-1">{title}</div>
      <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
      {subtitle && <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</div>}
    </div>
  )
}

export default function Overview() {
  const [days, setDays] = useState<(typeof RANGE_OPTIONS)[number]>(7)
  const [showTokens, setShowTokens] = useState(true)
  const [showSessions, setShowSessions] = useState(true)
  const [showCost, setShowCost] = useState(true)

  const { theme } = useTheme()
  const isDark =
    theme === 'dark' ||
    (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

  const { data: summary, isLoading: loadingSummary } = useQuery<SummaryResponse>({
    queryKey: ['summary', days],
    queryFn: () => fetchApi('/summary', { days })
  })

  const { data: daily, isLoading: loadingDaily } = useQuery<DailyResponse>({
    queryKey: ['daily', days],
    queryFn: () => fetchApi('/daily', { days })
  })

  if (loadingSummary || loadingDaily) {
    return <PageLoading title="Overview" subtitle="Loading usage metrics" cards={4} />
  }

  if (!summary || !daily) {
    return (
      <PageErrorState
        title="Unable to load overview"
        description="We could not load summary metrics right now. Try refreshing the page."
      />
    )
  }

  const chartData = daily.daily.map((entry) => {
      const parsed = new Date(entry.day)
      return {
        date: parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        tokens: entry.usage.total_tokens,
        cost: entry.cost_usd || 0,
        sessions: entry.total_sessions,
      }
    })

  const leftAxisTicks = showTokens || showSessions

  const axisColor = isDark ? '#9ca3af' : '#6b7280'
  const gridColor = isDark ? '#374151' : '#f3f4f6'
  const tooltipContentStyle = {
    backgroundColor: isDark ? '#1f2937' : '#ffffff',
    borderColor: isDark ? '#374151' : '#e5e7eb',
    color: isDark ? '#f9fafb' : '#111827',
  }
  const avgDailyTokens =
    chartData.length > 0
      ? Math.round(chartData.reduce((sum, point) => sum + point.tokens, 0) / chartData.length)
      : 0

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-end mb-6 sm:mb-8">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Overview</h1>
          <p className="text-gray-500 dark:text-gray-400">Last {days} days of OpenCode usage</p>
        </div>
        <div className="inline-flex rounded-lg border border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-900 p-1 gap-1">
          {RANGE_OPTIONS.map((option) => {
            const active = option === days
            return (
              <button
                key={option}
                className={`px-3 py-1.5 text-xs sm:text-sm rounded-md transition-colors ${
                  active
                    ? 'bg-blue-600 text-white'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
                }`}
                onClick={() => setDays(option)}
                type="button"
              >
                {option}d
              </button>
            )
          })}
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard 
          title="Total Cost" 
          value={summary.cost_usd ? formatUsd(summary.cost_usd) : 'N/A'}
          subtitle={summary.pricing_source ? "via models.dev" : "No pricing data"}
        />
        <StatCard 
          title="Total Tokens" 
          value={formatTokens(summary.usage.total_tokens)} 
        />
        <StatCard 
          title="Cache Read" 
          value={formatTokens(summary.usage.cache_read_tokens)} 
        />
        <StatCard 
          title="Sessions" 
          value={summary.total_sessions.toString()} 
        />
      </div>

      <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
        <div className="flex flex-wrap items-end justify-between gap-3 mb-6">
          <div>
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">Usage Trend</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Tokens, sessions, and spend across the selected window
            </p>
          </div>
          <div className="flex flex-col items-end gap-2">
            <div className="text-right">
              <div className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">
                Avg Daily Tokens
              </div>
              <div className="font-semibold text-gray-900 dark:text-gray-100">
                {formatTokens(avgDailyTokens)}
              </div>
            </div>
            <div className="flex flex-wrap justify-end gap-2 text-xs">
              <button
                className={`px-2.5 py-1 rounded-md border ${
                  showSessions
                    ? 'border-slate-300 bg-slate-100 text-slate-700 dark:border-slate-700 dark:bg-slate-800 dark:text-slate-200'
                    : 'border-gray-200 text-gray-500 dark:border-gray-700 dark:text-gray-500'
                }`}
                onClick={() => setShowSessions((value) => !value)}
                type="button"
              >
                Sessions
              </button>
              <button
                className={`px-2.5 py-1 rounded-md border ${
                  showTokens
                    ? 'border-blue-300 bg-blue-100 text-blue-700 dark:border-blue-800 dark:bg-blue-900/40 dark:text-blue-300'
                    : 'border-gray-200 text-gray-500 dark:border-gray-700 dark:text-gray-500'
                }`}
                onClick={() => setShowTokens((value) => !value)}
                type="button"
              >
                Tokens
              </button>
              <button
                className={`px-2.5 py-1 rounded-md border ${
                  showCost
                    ? 'border-emerald-300 bg-emerald-100 text-emerald-700 dark:border-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
                    : 'border-gray-200 text-gray-500 dark:border-gray-700 dark:text-gray-500'
                }`}
                onClick={() => setShowCost((value) => !value)}
                type="button"
              >
                Cost
              </button>
            </div>
          </div>
        </div>
        <div className="h-[22rem] sm:h-96">
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
              <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: axisColor }} />
              <YAxis
                yAxisId="left"
                axisLine={false}
                tickLine={false}
                tick={{ fill: axisColor }}
                hide={!leftAxisTicks}
                tickFormatter={(value: number | string) => formatTokens(Number(value))}
              />
              <YAxis
                yAxisId="right"
                orientation="right"
                axisLine={false}
                tickLine={false}
                tick={{ fill: axisColor }}
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
                  fill={isDark ? '#334155' : '#cbd5e1'}
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
                  stroke={isDark ? '#60a5fa' : '#2563eb'}
                  strokeWidth={2.5}
                  dot={{ r: 3, strokeWidth: 0, fill: isDark ? '#93c5fd' : '#3b82f6' }}
                  activeDot={{ r: 5 }}
                />
              ) : null}
              {showCost ? (
                <Line
                  yAxisId="right"
                  type="monotone"
                  dataKey="cost"
                  name="Cost"
                  stroke={isDark ? '#34d399' : '#059669'}
                  strokeWidth={2}
                  dot={false}
                  strokeDasharray="5 3"
                />
              ) : null}
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      </div>
    </div>
  )
}
