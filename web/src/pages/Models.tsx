import { useRef, useEffect, useState, useMemo } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft } from 'lucide-react'
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
import { providerColorFor } from '../lib/providerColors'
import type { ModelUsage } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import DaysFilterPicker from '../components/DaysFilterPicker'
import { useChartColors } from '../components/useChartColors'
import { useModelList } from '../hooks/useEntityList'

export default function Models() {
  const { providerId } = useParams<{ providerId: string }>()
  const { days } = useDaysFilter('models')
  const { sourceScope } = useSourceScope()
  const [chartMetric, setChartMetric] = useState<'tokens' | 'cost'>('tokens')
  const sentinelRef = useRef<HTMLDivElement>(null)
  const colors = useChartColors()

  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } = useModelList(
    { days, sourceScope, providerId }
  )

  const allModels = useMemo(
    () => data?.pages.flatMap((p) => p.models ?? []) ?? [],
    [data]
  )

  const chartData = useMemo(
    () => allModels.slice(0, 10).map((m) => ({
      name: (m.model_id.split('/').pop() || m.model_id).slice(0, 28),
      tokens: m.usage.total_tokens,
      cost: m.cost_usd ?? 0,
      fullName: m.model_id,
    })),
    [allModels]
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

  if (isLoading) return <PageLoading title="Models" subtitle="Loading model usage" cards={3} />
  if (isError || !data) {
    return (
      <PageErrorState
        title="Unable to load models"
        description="We could not fetch model usage right now. Try refreshing the page."
      />
    )
  }

  const firstPage = data.pages[0]

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <div className="mb-10 sm:mb-12 space-y-4">
        <Link
          to="/models"
          className="inline-flex items-center gap-2 text-sm text-[var(--text-tertiary)] hover:text-[var(--text-primary)] transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          Back to Providers
        </Link>
        <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
          <div className="min-w-0">
            <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)] break-all">
              {providerId ? `${providerId} Models` : 'Models'}
            </h1>
            <p className="mt-2 text-[var(--text-secondary)]">
              {firstPage.total_models} model{firstPage.total_models !== 1 ? 's' : ''} &middot;{' '}
              {days === 1 ? 'last 24 hours' : `last ${days} days`}
            </p>
          </div>
          <DaysFilterPicker scope="models" />
        </div>
      </div>

      {chartData.length > 0 && (
        <div className="ds-surface p-4 sm:p-5 mb-6 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
              Model Distribution
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
                width={136}
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

      {allModels.length === 0 ? (
        <div className="ds-surface flex flex-col items-center justify-center py-16 gap-3 text-center">
          <p className="font-medium text-[var(--text-secondary)]">No model usage found in this period.</p>
          <p className="text-sm text-[var(--text-tertiary)]">Start using models to see usage data here.</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {allModels.map((m, i) => (
            <ModelCard key={m.model_id} model={m} index={i} />
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

function ModelCard({ model, index }: { model: ModelUsage; index: number }) {
  const color = providerColorFor(model.provider)
  const shortName = model.model_id.split('/').pop() || model.model_id

  return (
    <Link
      to={`/models/${encodeURIComponent(model.model_id)}`}
      className="ds-surface focus-ring flex flex-col p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md animate-slide-up"
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <div
            className="font-medium text-[var(--text-primary)] truncate text-sm"
            title={model.model_id}
          >
            {shortName}
          </div>
          {shortName !== model.model_id && (
            <div className="text-xs text-[var(--text-tertiary)] truncate mt-0.5">
              {model.model_id}
            </div>
          )}
        </div>
        {model.provider && (
          <span
            className="shrink-0 inline-block px-2 py-0.5 text-xs font-medium rounded-full"
            style={{ backgroundColor: color.bg, color: color.text }}
          >
            {model.provider}
          </span>
        )}
      </div>

      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[var(--border-subtle)]">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Sessions
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {model.total_sessions}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Tokens
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {formatTokens(model.usage.total_tokens)}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Cost
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {model.cost_usd != null ? formatUsd(model.cost_usd) : '–'}
          </div>
        </div>
      </div>
    </Link>
  )
}
