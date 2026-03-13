import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, Clock, Terminal, Box } from 'lucide-react'
import { buildApiUrl, fetchApi } from '../lib/api'
import { formatTokens, formatUsd, cn } from '../lib/utils'
import type { LiveSnapshotResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'

export default function Live() {
  const [streamData, setStreamData] = useState<LiveSnapshotResponse | null>(null)
  const [streamMode, setStreamMode] = useState<'connecting' | 'streaming' | 'polling'>(() =>
    typeof window !== 'undefined' && typeof window.EventSource !== 'undefined'
      ? 'connecting'
      : 'polling'
  )

  const { data: polledData, isError: pollingError } = useQuery<LiveSnapshotResponse>({
    queryKey: ['live'],
    queryFn: () => fetchApi('/live/snapshot', { window_minutes: 60 }),
    refetchInterval: 3000,
    enabled: streamMode === 'polling',
  })

  useEffect(() => {
    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      return
    }

    const eventsUrl = buildApiUrl('/live/events', { window_minutes: 60, interval_seconds: 3 })
    const source = new window.EventSource(eventsUrl)

    const onSnapshot = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as LiveSnapshotResponse
        setStreamData(parsed)
        setStreamMode('streaming')
      } catch {
        source.close()
        setStreamMode('polling')
      }
    }

    const onError = () => {
      source.close()
      setStreamMode('polling')
    }

    source.addEventListener('live.snapshot', onSnapshot as EventListener)
    source.addEventListener('live.error', onError)
    source.onerror = onError

    return () => {
      source.removeEventListener('live.snapshot', onSnapshot as EventListener)
      source.removeEventListener('live.error', onError)
      source.close()
    }
  }, [])

  const data = useMemo(() => streamData ?? polledData ?? null, [streamData, polledData])

  if (streamMode === 'polling' && pollingError) {
    return (
      <PageErrorState
        title="Unable to load live monitoring"
        description="Live polling fallback failed. Check server availability and try again."
      />
    )
  }
  if (!data) {
    const subtitle =
      streamMode === 'connecting'
        ? 'Connecting to real-time stream'
        : 'Using polling fallback while waiting for first snapshot'
    return <PageLoading title="Live Monitoring" subtitle={subtitle} cards={3} />
  }

  const isActuallyActive = data.active_session?.is_active
  const transportLabel =
    streamMode === 'streaming' ? 'Real-time stream' : streamMode === 'polling' ? 'Polling fallback' : 'Connecting...'

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto space-y-6 w-full min-w-0">
      <div className="flex items-center justify-between mb-4 sm:mb-8">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              {isActuallyActive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
              <span className={cn("relative inline-flex rounded-full h-3 w-3", isActuallyActive ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600")}></span>
            </span>
            Live Monitoring
          </h1>
          <p className="text-gray-500 dark:text-gray-400">Rolling 60-minute window · {transportLabel}</p>
        </div>
      </div>

      {data.active_session && (
        <div className={cn(
          "p-4 sm:p-6 rounded-xl border transition-colors",
          isActuallyActive 
            ? "bg-blue-50/50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800/50" 
            : "bg-white dark:bg-gray-900 border-gray-200 dark:border-gray-800"
        )}>
          <div className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400 mb-2">
            <Activity className="w-4 h-4" />
            {isActuallyActive ? 'Active Session' : 'Last Session'}
          </div>
          <div className="text-lg sm:text-xl font-bold text-gray-900 dark:text-white truncate">
            {data.active_session.title || data.active_session.session_id}
          </div>
          <div className="text-sm text-gray-500 dark:text-gray-400 mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Updated {new Date(data.active_session.last_updated_ms).toLocaleTimeString()}
          </div>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Tokens</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">{formatTokens(data.usage.total_tokens)}</div>
        </div>
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Cost</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">{data.cost_usd ? formatUsd(data.cost_usd) : 'N/A'}</div>
        </div>
        <div className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm transition-colors">
          <div className="text-sm text-gray-500 dark:text-gray-400">Interactions</div>
          <div className="text-2xl sm:text-3xl font-bold text-gray-900 dark:text-gray-100">{data.total_interactions}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 min-w-0">
        <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
          <div className="px-6 py-4 border-b border-gray-100 dark:border-gray-800 bg-gray-50/50 dark:bg-gray-800/50 flex items-center gap-2 font-medium text-gray-900 dark:text-gray-100">
            <Box className="w-4 h-4" /> Models
          </div>
          <div className="p-0">
            {data.top_models.map(m => (
                <div key={m.model_id} className="flex justify-between items-center gap-4 px-4 sm:px-6 py-3 border-b border-gray-50 dark:border-gray-800/50 last:border-0">
                  <div className="font-medium text-sm text-gray-900 dark:text-gray-100 flex-1 min-w-0 truncate">{m.model_id}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 font-mono shrink-0">{formatTokens(m.usage.total_tokens)}</div>
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
                <div key={t.tool_name} className="flex justify-between items-center gap-4 px-4 sm:px-6 py-3 border-b border-gray-50 dark:border-gray-800/50 last:border-0">
                  <div className="font-medium text-sm text-gray-900 dark:text-gray-100 flex-1 min-w-0 truncate">{t.tool_name}</div>
                  <div className="text-sm text-gray-500 dark:text-gray-400 font-mono shrink-0">{t.total_calls} calls</div>
                </div>
              ))}
            {data.top_tools.length === 0 && <div className="p-6 text-sm text-gray-500 dark:text-gray-400 text-center">No tool activity</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
