import { useQuery } from '@tanstack/react-query'
import { Activity, Clock, Terminal, Box } from 'lucide-react'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd, cn } from '../lib/utils'

interface LiveSnapshot {
  generated_at_ms: number
  window_minutes: number
  total_interactions: number
  total_sessions: number
  usage: { total_tokens: number; input_tokens: number; output_tokens: number }
  cost_usd: number | null
  active_session: {
    session_id: string
    title: string | null
    is_active: boolean
    last_updated_ms: number
  } | null
  top_models: Array<{ model_id: string; usage: { total_tokens: number }; cost_usd: number | null }>
  top_tools: Array<{ tool_name: string; total_calls: number }>
}

export default function Live() {
  const { data, isError } = useQuery<LiveSnapshot>({
    queryKey: ['live'],
    queryFn: () => fetchApi('/live/snapshot', { window_minutes: 60 }),
    refetchInterval: 3000 // Poll every 3s
  })

  if (isError) return <div className="p-8 text-red-500 dark:text-red-400">Failed to load live data.</div>
  if (!data) return <div className="p-8 text-gray-500 dark:text-gray-400">Waiting for heartbeat...</div>

  const isActuallyActive = data.active_session?.is_active

  return (
    <div className="p-8 max-w-5xl mx-auto space-y-6">
      <div className="flex items-center justify-between mb-8">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              {isActuallyActive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
              <span className={cn("relative inline-flex rounded-full h-3 w-3", isActuallyActive ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600")}></span>
            </span>
            Live Monitoring
          </h1>
          <p className="text-gray-500 dark:text-gray-400">Rolling 60-minute window</p>
        </div>
      </div>

      {data.active_session && (
        <div className={cn(
          "p-6 rounded-xl border transition-colors",
          isActuallyActive 
            ? "bg-blue-50/50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800/50" 
            : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
        )}>
          <div className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400 mb-2">
            <Activity className="w-4 h-4" />
            {isActuallyActive ? 'Active Session' : 'Last Session'}
          </div>
          <div className="text-xl font-bold text-gray-900 dark:text-white truncate">
            {data.active_session.title || data.active_session.session_id}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Updated {new Date(data.active_session.last_updated_ms).toLocaleTimeString()}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Tokens</div>
          <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">{formatTokens(data.usage.total_tokens)}</div>
        </div>
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Cost</div>
          <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data.cost_usd ? formatUsd(data.cost_usd) : 'N/A'}</div>
        </div>
        <div className="bg-white dark:bg-gray-900 p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Interactions</div>
          <div className="text-3xl font-bold text-gray-900 dark:text-gray-100">{data.total_interactions}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50 flex items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
            <Box className="w-4 h-4" /> Models
          </div>
          <div className="p-0">
            {data.top_models.map(m => (
              <div key={m.model_id} className="flex justify-between items-center px-6 py-3 border-b border-gray-50 dark:border-gray-800/50 last:border-0">
                <div className="font-medium text-sm text-gray-900 dark:text-gray-100">{m.model_id}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">{formatTokens(m.usage.total_tokens)}</div>
              </div>
            ))}
            {data.top_models.length === 0 && <div className="p-6 text-sm text-gray-500 dark:text-gray-400 text-center">No model activity</div>}
          </div>
        </div>

        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50 flex items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
            <Terminal className="w-4 h-4" /> Tools
          </div>
          <div className="p-0">
            {data.top_tools.map(t => (
              <div key={t.tool_name} className="flex justify-between items-center px-6 py-3 border-b border-gray-50 dark:border-gray-800/50 last:border-0">
                <div className="font-medium text-sm text-gray-900 dark:text-gray-100">{t.tool_name}</div>
                <div className="text-sm text-gray-500 dark:text-gray-400 font-mono">{t.total_calls} calls</div>
              </div>
            ))}
            {data.top_tools.length === 0 && <div className="p-6 text-sm text-gray-500 dark:text-gray-400 text-center">No tool activity</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
