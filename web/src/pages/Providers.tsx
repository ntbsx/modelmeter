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
import { providerColorFor } from '../lib/providerColors'
import type { ProviderUsage } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import { useDaysFilter } from '../hooks/useDaysFilter'
import { PageHeader } from '../components/DataTable'
import DaysFilterPicker from '../components/DaysFilterPicker'
import { useChartColors } from '../components/useChartColors'
import { useProviderList } from '../hooks/useEntityList'

export default function Providers() {
  const { days } = useDaysFilter('providers')
  const { sourceScope } = useSourceScope()
  const [chartMetric, setChartMetric] = useState<'tokens' | 'cost'>('tokens')
  const sentinelRef = useRef<HTMLDivElement>(null)
  const colors = useChartColors()

  const { data, isLoading, isError, fetchNextPage, hasNextPage, isFetchingNextPage } =
    useProviderList({ days, sourceScope })

  const allProviders = useMemo(
    () => data?.pages.flatMap((p) => p.providers ?? []) ?? [],
    [data]
  )

  const chartData = useMemo(
    () => allProviders.slice(0, 10).map((p) => ({
      name: p.provider.length > 16 ? p.provider.slice(0, 15) + '…' : p.provider,
      tokens: p.usage.total_tokens,
      cost: p.cost_usd ?? 0,
      fullName: p.provider,
    })),
    [allProviders]
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

  if (isLoading) return <PageLoading title="Providers" subtitle="Loading provider usage" cards={3} />
  if (isError || !data) {
    return (
      <PageErrorState
        title="Unable to load providers"
        description="We could not fetch provider usage right now. Try refreshing the page."
      />
    )
  }

  const firstPage = data.pages[0]

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <PageHeader
        title="Providers"
        description={`${firstPage.total_providers} provider${firstPage.total_providers !== 1 ? 's' : ''} \u00b7 ${days === 1 ? 'last 24 hours' : `last ${days} days`}`}
        actions={<DaysFilterPicker scope="providers" />}
      />

      {chartData.length > 0 && (
        <div className="ds-surface p-4 sm:p-5 mb-6 animate-slide-up">
          <div className="flex items-center justify-between mb-4">
            <span className="text-xs font-medium uppercase tracking-wider text-[var(--text-tertiary)]">
              Provider Distribution
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

      {allProviders.length === 0 ? (
        <div className="ds-surface flex flex-col items-center justify-center py-16 gap-3 text-center">
          <p className="font-medium text-[var(--text-secondary)]">No provider usage found in this period.</p>
          <p className="text-sm text-[var(--text-tertiary)]">
            Make API calls to start tracking usage across your providers.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {allProviders.map((p, i) => (
            <ProviderCard key={p.provider} provider={p} index={i} />
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

function ProviderCard({ provider, index }: { provider: ProviderUsage; index: number }) {
  const color = providerColorFor(provider.provider)

  return (
    <Link
      to={`/models/provider/${encodeURIComponent(provider.provider)}`}
      className="ds-surface focus-ring flex flex-col p-4 transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md animate-slide-up"
      style={{ animationDelay: `${Math.min(index, 8) * 40}ms` }}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <span
          className="inline-block px-2.5 py-0.5 text-sm font-semibold rounded-full truncate max-w-[12rem]"
          style={{ backgroundColor: color.bg, color: color.text }}
          title={provider.provider}
        >
          {provider.provider}
        </span>
        <span className="text-xs text-[var(--text-tertiary)]">
          {provider.total_models} model{provider.total_models !== 1 ? 's' : ''}
        </span>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-3 border-t border-[var(--border-subtle)]">
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Interactions
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {provider.total_interactions.toLocaleString()}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Tokens
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {formatTokens(provider.usage.total_tokens)}
          </div>
        </div>
        <div>
          <div className="text-xs uppercase tracking-wider text-[var(--text-tertiary)] mb-0.5">
            Cost
          </div>
          <div className="text-sm font-mono font-medium text-[var(--text-primary)]">
            {provider.cost_usd != null ? formatUsd(provider.cost_usd) : '–'}
          </div>
        </div>
      </div>
    </Link>
  )
}
