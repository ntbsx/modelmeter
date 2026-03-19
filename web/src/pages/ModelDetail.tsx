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
import PageLoading from '../components/PageLoading'
import { PageEmptyState, PageErrorState } from '../components/PageState'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { StatCard } from '../components/ui'
import { SectionHeader } from '../components/DataTable'
import { useChartColors } from '../components/useChartColors'

export default function ModelDetail() {
  const { modelId } = useParams()
  const decodedModelId = decodeURIComponent(modelId ?? '')
  const { days } = useDaysFilter()
  const chartColors = useChartColors()

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

  const tooltipContentStyle = {
    backgroundColor: chartColors.tooltip.background,
    borderColor: chartColors.tooltip.border,
    color: chartColors.tooltip.text,
  }

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <div className="mb-8 sm:mb-10 space-y-3">
        <Link
          className="inline-flex items-center gap-2 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
          to={`/models/provider/${encodeURIComponent(data.provider)}`}
        >
          <ArrowLeft className="h-4 w-4" />
          Back to {data.provider} Models
        </Link>

        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div className="min-w-0">
            <h1 className="ds-text-heading break-all">
              {data.model_id}
            </h1>
            <p className="mt-2 text-[var(--text-tertiary)]">
              Model usage for the {days === 1 ? 'last 24 hours' : `last ${days} days`}
            </p>
          </div>
        </div>
      </div>

      <section className="mb-8 sm:mb-10">
        <h2 className="ds-text-label-uppercase mb-4">Overview</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          <StatCard label="Sessions" value={data.total_sessions.toString()} />
          <StatCard label="Interactions" value={data.total_interactions.toString()} />
          <StatCard label="Total Tokens" value={formatTokens(data.usage.total_tokens)} />
          <StatCard
            label="Cost"
            value={data.cost_usd ? formatUsd(data.cost_usd) : 'N/A'}
            subtitle={data.pricing_source ? 'via models.dev' : 'No pricing data'}
          />
        </div>
      </section>

      <section className="mb-8 sm:mb-10">
        <h2 className="ds-text-label-uppercase mb-4">Token Breakdown</h2>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 sm:gap-5">
          <StatCard label="Input Tokens" value={formatTokens(data.usage.input_tokens)} />
          <StatCard label="Output Tokens" value={formatTokens(data.usage.output_tokens)} />
          <StatCard label="Cache Read" value={formatTokens(data.usage.cache_read_tokens)} />
          <StatCard label="Cache Write" value={formatTokens(data.usage.cache_write_tokens)} />
        </div>
      </section>

      {chartData.length > 0 && (
        <section className="ds-surface overflow-hidden">
          <div className="p-5 sm:p-8 border-b border-[var(--border-subtle)]">
            <SectionHeader
              title="Daily Usage"
              description="Token usage and cost over time"
            />
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
                  tickFormatter={(value: number | string) => formatTokens(Number(value))}
                />
                <YAxis
                  yAxisId="right"
                  orientation="right"
                  axisLine={false}
                  tickLine={false}
                  tick={{ fill: chartColors.axis }}
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
                  fill={chartColors.sessions.fill}
                  radius={[4, 4, 0, 0]}
                  maxBarSize={28}
                />
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
              </ComposedChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </div>
  )
}
