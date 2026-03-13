import { useQuery } from '@tanstack/react-query'
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, AreaChart, Area } from 'recharts'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'
import type { DailyResponse, SummaryResponse } from '../types'
import { useTheme } from '../components/ThemeProvider'

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
  const { theme } = useTheme()
  const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

  const { data: summary, isLoading: loadingSummary } = useQuery<SummaryResponse>({
    queryKey: ['summary'],
    queryFn: () => fetchApi('/summary', { days: 7 })
  })

  const { data: daily, isLoading: loadingDaily } = useQuery<DailyResponse>({
    queryKey: ['daily'],
    queryFn: () => fetchApi('/daily', { days: 7 })
  })

  if (loadingSummary || loadingDaily) return <div className="px-4 py-6 sm:p-8 text-gray-500 dark:text-gray-400">Loading...</div>

  const chartData = daily?.daily.map(d => ({
    date: d.day.slice(5), // MM-DD
    tokens: d.usage.total_tokens,
    cost: d.cost_usd || 0
  })) || []

  const axisColor = isDark ? '#9ca3af' : '#6b7280'
  const gridColor = isDark ? '#374151' : '#f3f4f6'
  const tooltipContentStyle = {
    backgroundColor: isDark ? '#1f2937' : '#ffffff',
    borderColor: isDark ? '#374151' : '#e5e7eb',
    color: isDark ? '#f9fafb' : '#111827',
  }
  const cursorColor = isDark ? '#374151' : '#f3f4f6'

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto">
      <div className="flex justify-between items-end mb-6 sm:mb-8">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Overview</h1>
          <p className="text-gray-500 dark:text-gray-400">Last 7 days of OpenCode usage</p>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-8">
        <StatCard 
          title="Total Cost" 
          value={summary?.cost_usd ? formatUsd(summary.cost_usd) : 'N/A'}
          subtitle={summary?.pricing_source ? "via models.dev" : "No pricing data"}
        />
        <StatCard 
          title="Total Tokens" 
          value={formatTokens(summary?.usage.total_tokens || 0)} 
        />
        <StatCard 
          title="Cache Read" 
          value={formatTokens(summary?.usage.cache_read_tokens || 0)} 
        />
        <StatCard 
          title="Sessions" 
          value={summary?.total_sessions.toString() || '0'} 
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 sm:gap-8">
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <h3 className="text-lg font-bold mb-6 text-gray-900 dark:text-white">Token Volume</h3>
          <div className="h-64 sm:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: axisColor}} />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: axisColor}}
                  tickFormatter={(val: any) => formatTokens(Number(val))}
                />
                <Tooltip 
                  formatter={(val: any) => [formatTokens(Number(val)), 'Tokens']}
                  cursor={{fill: cursorColor}}
                  contentStyle={tooltipContentStyle}
                />
                <Bar dataKey="tokens" fill="#3b82f6" radius={[4, 4, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <h3 className="text-lg font-bold mb-6 text-gray-900 dark:text-white">Cost Spend</h3>
          <div className="h-64 sm:h-72">
            <ResponsiveContainer width="100%" height="100%">
              <AreaChart data={chartData}>
                <defs>
                  <linearGradient id="colorCost" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="5%" stopColor="#10b981" stopOpacity={0.3}/>
                    <stop offset="95%" stopColor="#10b981" stopOpacity={0}/>
                  </linearGradient>
                </defs>
                <CartesianGrid strokeDasharray="3 3" vertical={false} stroke={gridColor} />
                <XAxis dataKey="date" axisLine={false} tickLine={false} tick={{fill: axisColor}} />
                <YAxis 
                  axisLine={false} 
                  tickLine={false} 
                  tick={{fill: axisColor}}
                  tickFormatter={(val: any) => '$' + Number(val).toFixed(2)}
                />
                <Tooltip 
                  formatter={(val: any) => [formatUsd(Number(val)), 'Cost']}
                  contentStyle={tooltipContentStyle}
                />
                <Area type="monotone" dataKey="cost" stroke="#10b981" fillOpacity={1} fill="url(#colorCost)" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      </div>
    </div>
  )
}
