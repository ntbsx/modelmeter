import { useQuery } from '@tanstack/react-query'
import { ArrowLeft } from 'lucide-react'
import { Link, useParams } from 'react-router-dom'
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
import type { ModelDetailResponse } from '../types'
import { useTheme } from '../components/useTheme'
import PageLoading from '../components/PageLoading'
import { PageEmptyState, PageErrorState } from '../components/PageState'
import { useDaysFilter } from '../hooks/useDaysFilter'

function StatCard({ title, value, subtitle }: { title: string; value: string; subtitle?: string }) {
  return (
    <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
      <div className="text-sm text-gray-500 dark:text-gray-400">{title}</div>
      <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">{value}</div>
      {subtitle && <div className="text-xs text-gray-400 dark:text-gray-500 mt-1">{subtitle}</div>}
    </div>
  )
}

export default function ModelDetail() {
  const { modelId } = useParams()
  const decodedModelId = decodeURIComponent(modelId ?? '')
  const { days } = useDaysFilter()

  const { theme } = useTheme()
  const isDark =
    theme === 'dark' ||
    (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

  const { data, isLoading, error } = useQuery<ModelDetailResponse>({
    queryKey: ['model-detail', decodedModelId, days],
    queryFn: () => fetchApi(`/models/${encodeURIComponent(decodedModelId)}`, { days }),
    enabled: decodedModelId.length > 0,
  })

  if (!decodedModelId) {
    return (
      <PageErrorState
        title="Invalid model ID"
        description="The requested model identifier is not valid."
        action={
          <Link
            className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            to="/models"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Providers
          </Link>
        }
      />
    )
  }

  if (isLoading) {
    return <PageLoading title="Model Detail" subtitle="Loading model usage" cards={4} />
  }

  if (error) {
    return (
      <PageErrorState
        title="Unable to load model details"
        description="We could not fetch usage for this model. Please refresh and try again."
        action={
          <Link
            className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            to="/models"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Providers
          </Link>
        }
      />
    )
  }

  if (!data) {
    return (
      <PageEmptyState
        title="Model not found"
        description="No usage data was found for this model in the selected window."
        action={
          <Link
            className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
            to="/models"
          >
            <ArrowLeft className="h-4 w-4" />
            Back to Providers
          </Link>
        }
      />
    )
  }

  const chartData = (data.daily ?? []).map((entry) => {
    const [year, month, day] = entry.day.split('-').map(Number)
    const parsed = new Date(year, (month || 1) - 1, day || 1)
    return {
      date: parsed.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      tokens: entry.usage.total_tokens,
      cost: entry.cost_usd || 0,
      sessions: entry.total_sessions,
    }
  })

  const axisColor = isDark ? '#9ca3af' : '#6b7280'
  const gridColor = isDark ? '#374151' : '#f3f4f6'
  const tooltipContentStyle = {
    backgroundColor: isDark ? '#1f2937' : '#ffffff',
    borderColor: isDark ? '#374151' : '#e5e7eb',
    color: isDark ? '#f9fafb' : '#111827',
  }

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto space-y-6 w-full min-w-0">
      <div className="space-y-3">
        <Link
          className="inline-flex items-center gap-2 text-sm text-blue-700 hover:text-blue-800 dark:text-blue-400 dark:hover:text-blue-300"
          to={`/models/provider/${encodeURIComponent(data.provider)}`}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {data.provider} Models
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white break-all">
              {data.model_id}
            </h1>
            <p className="text-gray-500 dark:text-gray-400 mt-1">
              Model usage for the {days === 1 ? 'last 24 hours' : `last ${days} days`}
            </p>
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Sessions" value={data.total_sessions.toString()} />
        <StatCard title="Interactions" value={data.total_interactions.toString()} />
        <StatCard title="Total Tokens" value={formatTokens(data.usage.total_tokens)} />
        <StatCard
          title="Cost"
          value={data.cost_usd ? formatUsd(data.cost_usd) : 'N/A'}
          subtitle={data.pricing_source ? 'via models.dev' : 'No pricing data'}
        />
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard title="Input Tokens" value={formatTokens(data.usage.input_tokens)} />
        <StatCard title="Output Tokens" value={formatTokens(data.usage.output_tokens)} />
        <StatCard title="Cache Read" value={formatTokens(data.usage.cache_read_tokens)} />
        <StatCard title="Cache Write" value={formatTokens(data.usage.cache_write_tokens)} />
      </div>

      {chartData.length > 0 && (
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="mb-6">
            <h3 className="text-lg font-bold text-gray-900 dark:text-white">Daily Usage</h3>
            <p className="text-sm text-gray-500 dark:text-gray-400">
              Token usage and cost over time
            </p>
          </div>
          <div className="h-[20rem] sm:h-80">
            <ResponsiveContainer width="100%" height="100%">
              <ComposedChart data={chartData} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{ fill: axisColor }} />
                <YAxis
                  yAxisId="left"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: axisColor }}
                  tickFormatter={(value: number | string) => formatTokens(Number(value))}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: axisColor }}
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
                <Bar
                  yAxisId="left"
                  dataKey="sessions"
                  name="Sessions"
                  fill={isDark ? '#334155' : '#cbd5e1'}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={28}
                />
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
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  )
}
