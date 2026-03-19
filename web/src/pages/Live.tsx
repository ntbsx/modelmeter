import { useEffect, useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Activity, Clock, Terminal, Box } from 'lucide-react'
import { buildApiUrl, fetchApi, getAuthToken } from '../lib/api'
import { formatTokens, formatUsd, cn } from '../lib/utils'
import type { LiveSnapshotResponse } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { useSourceScope } from '../hooks/useSourceScope'
import SourceStatusBanner from '../components/SourceStatusBanner'

export default function Live() {
  const [streamData, setStreamData] = useState<LiveSnapshotResponse | null>(null)
  const [isPaused, setIsPaused] = useState(false)
  const [streamMode, setStreamMode] = useState<'connecting' | 'streaming' | 'polling'>(() =>
    typeof window !== 'undefined' && typeof window.EventSource !== 'undefined'
      ? 'connecting'
      : 'polling'
  )
  const [reconnectCountdownSeconds, setReconnectCountdownSeconds] = useState<number | null>(null)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)
  const { sourceScope } = useSourceScope()
  const liveScope = sourceScope === 'self' ? sourceScope : 'self'

  const { data: polledData, isError: pollingError } = useQuery<LiveSnapshotResponse>({
    queryKey: ['live', liveScope],
    queryFn: () => fetchApi('/live/snapshot', { window_minutes: 60, source_scope: liveScope }),
    refetchInterval: 3000,
    enabled: streamMode === 'polling' && !isPaused,
  })

  useEffect(() => {
    if (isPaused) {
      return
    }

    if (typeof window === 'undefined' || typeof window.EventSource === 'undefined') {
      return
    }

    if (streamMode !== 'connecting') {
      return
    }

    const authToken = getAuthToken()
    const eventsParams: Record<string, string | number> = {
      window_minutes: 60,
      interval_seconds: 3,
      source_scope: liveScope,
    }
    if (authToken) {
      // NOTE: Token in query string is visible in browser history and server logs.
      // This is an inherent limitation of EventSource which cannot set custom headers.
      // The backend validates this token identically to the Authorization header.
      eventsParams._auth = authToken
    }
    const eventsUrl = buildApiUrl('/live/events', eventsParams)
    const source = new window.EventSource(eventsUrl)

    const onSnapshot = (event: MessageEvent<string>) => {
      try {
        const parsed = JSON.parse(event.data) as LiveSnapshotResponse
        setStreamData(parsed)
        setStreamMode('streaming')
        setReconnectCountdownSeconds(null)
      } catch {
        source.close()
        setStreamMode('polling')
      }
    }

    const onError = () => {
      source.close()
      setStreamMode('polling')
      setReconnectCountdownSeconds(5)
    }

    source.addEventListener('live.snapshot', onSnapshot as EventListener)
    source.addEventListener('live.error', onError)
    source.onerror = onError

    return () => {
      source.removeEventListener('live.snapshot', onSnapshot as EventListener)
      source.removeEventListener('live.error', onError)
      source.close()
    }
  }, [isPaused, reconnectAttempt, liveScope, streamMode])

  useEffect(() => {
    if (isPaused || streamMode !== 'polling' || reconnectCountdownSeconds === null) {
      return
    }

    if (reconnectCountdownSeconds <= 0) {
      const reconnectTimer = window.setTimeout(() => {
        setReconnectCountdownSeconds(null)
        setReconnectAttempt((value) => value + 1)
        setStreamMode('connecting')
      }, 0)

      return () => window.clearTimeout(reconnectTimer)
    }

    const timer = window.setTimeout(() => {
      setReconnectCountdownSeconds((value) => {
        if (value === null) {
          return null
        }
        return Math.max(0, value - 1)
      })
    }, 1000)

    return () => window.clearTimeout(timer)
  }, [isPaused, reconnectCountdownSeconds, streamMode])

  const data = useMemo(() => streamData ?? polledData ?? null, [streamData, polledData])

  const handlePauseToggle = () => {
    setIsPaused((current) => {
      const next = !current
      if (next) {
        setReconnectCountdownSeconds(null)
        setStreamMode('polling')
      } else {
        setReconnectAttempt((value) => value + 1)
        setStreamMode('connecting')
      }
      return next
    })
  }

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
      isPaused
        ? 'Updates are paused'
        : streamMode === 'connecting'
        ? 'Connecting to real-time stream'
        : 'Using polling fallback while waiting for first snapshot'
    return <PageLoading title="Live Monitoring" subtitle={subtitle} cards={3} />
  }

  const isActuallyActive = data.active_session?.is_active
  const transportLabel = isPaused
    ? 'Paused'
    : streamMode === 'streaming'
      ? 'Real-time stream'
      : streamMode === 'polling'
        ? reconnectCountdownSeconds !== null
          ? `Polling fallback · reconnecting in ${reconnectCountdownSeconds}s`
          : 'Polling fallback'
        : 'Connecting...'
  const transportBadgeClasses = isPaused
    ? 'bg-amber-100 text-amber-800 dark:bg-amber-900/40 dark:text-amber-300'
    : streamMode === 'streaming'
      ? 'bg-emerald-100 text-emerald-800 dark:bg-emerald-900/40 dark:text-emerald-300'
      : streamMode === 'polling'
        ? 'bg-[var(--surface-secondary)] text-[var(--text-secondary)]'
        : 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300'

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto space-y-6 w-full min-w-0">
      <div className="flex flex-col sm:flex-row sm:items-start sm:justify-between gap-4">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)] flex items-center gap-3">
            <span className="relative flex h-3 w-3">
              {isActuallyActive && <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-green-400 opacity-75"></span>}
              <span className={cn("relative inline-flex rounded-full h-3 w-3", isActuallyActive ? "bg-green-500" : "bg-gray-300 dark:bg-gray-600")}></span>
            </span>
            Live Monitoring
          </h1>
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <p className="text-[var(--text-secondary)]">Rolling 60-minute window</p>
            <span className={`inline-flex items-center rounded-full px-2.5 py-1 text-xs font-medium ${transportBadgeClasses}`}>
              {transportLabel}
            </span>
          </div>
        </div>
        <button
          className={cn(
            'rounded-lg border px-4 py-2 text-sm font-medium transition-colors shrink-0',
            isPaused
              ? 'border-emerald-200 bg-emerald-50 text-emerald-700 hover:bg-emerald-100 dark:border-emerald-800 dark:bg-emerald-900/30 dark:text-emerald-300'
              : 'border-amber-200 bg-amber-50 text-amber-700 hover:bg-amber-100 dark:border-amber-800 dark:bg-amber-900/30 dark:text-amber-300'
          )}
          onClick={handlePauseToggle}
          type="button"
        >
          {isPaused ? 'Resume Updates' : 'Pause Updates'}
        </button>
      </div>

      <SourceStatusBanner
        isLoading={false}
        isFetching={false}
        sourceScope={sourceScope}
        sourcesConsidered={[]}
        sourcesSucceeded={[]}
        sourcesFailed={[]}
        hasData={true}
        healthCheckSupport={false}
      />

      {data.active_session && (
        <div className={cn(
          "p-5 sm:p-6 rounded-xl border transition-colors",
          isActuallyActive 
            ? "bg-blue-50/50 dark:bg-blue-900/20 border-blue-100 dark:border-blue-800/50" 
            : "bg-[var(--surface-primary)] border-[var(--border-default)]"
        )}>
          <div className="flex items-center gap-2 text-sm font-medium text-blue-600 dark:text-blue-400 mb-2">
            <Activity className="w-4 h-4" />
            {isActuallyActive ? 'Active Session' : 'Last Session'}
          </div>
          <div className="text-lg sm:text-xl font-bold text-[var(--text-primary)] truncate">
            {data.active_session.title || data.active_session.session_id}
          </div>
          <div className="text-sm text-[var(--text-secondary)] mt-1.5 flex items-center gap-1.5">
            <Clock className="w-3.5 h-3.5" />
            Updated {new Date(data.active_session.last_updated_ms).toLocaleTimeString()}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-4 sm:gap-5">
        <div className="ds-surface p-5 sm:p-6">
          <div className="ds-text-label">Tokens</div>
          <div className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1 ds-text-tabular">{formatTokens(data.usage.total_tokens)}</div>
        </div>
        <div className="ds-surface p-5 sm:p-6">
          <div className="ds-text-label">Cost</div>
          <div className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1 ds-text-tabular">{data.cost_usd ? formatUsd(data.cost_usd) : 'N/A'}</div>
        </div>
        <div className="ds-surface p-5 sm:p-6">
          <div className="ds-text-label">Interactions</div>
          <div className="text-xl sm:text-2xl font-bold tracking-tight text-[var(--text-primary)] mt-1 ds-text-tabular">{data.total_interactions}</div>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 min-w-0">
        <div className="ds-surface overflow-hidden">
          <div className="px-5 sm:px-6 py-4 border-b border-[var(--border-subtle)]">
            <h2 className="ds-text-subheading flex items-center gap-2">
              <Box className="w-4 h-4" /> Models
            </h2>
          </div>
          <div className="p-0">
            {(data.top_models ?? []).map(m => (
                <div key={m.model_id} className="flex justify-between items-center gap-4 px-5 sm:px-6 py-3.5 border-b border-[var(--border-subtle)] last:border-0">
                  <div className="font-medium text-sm text-[var(--text-primary)] flex-1 min-w-0 truncate">{m.model_id}</div>
                  <div className="text-sm text-[var(--text-secondary)] font-mono shrink-0">{formatTokens(m.usage.total_tokens)}</div>
                </div>
              ))}
            {(data.top_models ?? []).length === 0 && <div className="p-6 text-sm text-[var(--text-secondary)] text-center">No model activity</div>}
          </div>
        </div>

        <div className="ds-surface overflow-hidden">
          <div className="px-5 sm:px-6 py-4 border-b border-[var(--border-subtle)]">
            <h2 className="ds-text-subheading flex items-center gap-2">
              <Terminal className="w-4 h-4" /> Tools
            </h2>
          </div>
          <div className="p-0">
            {(data.top_tools ?? []).map(t => (
                <div key={t.tool_name} className="flex justify-between items-center gap-4 px-5 sm:px-6 py-3.5 border-b border-[var(--border-subtle)] last:border-0">
                  <div className="font-medium text-sm text-[var(--text-primary)] flex-1 min-w-0 truncate">{t.tool_name}</div>
                  <div className="text-sm text-[var(--text-secondary)] font-mono shrink-0">{t.total_calls} calls</div>
                </div>
              ))}
            {(data.top_tools ?? []).length === 0 && <div className="p-6 text-sm text-[var(--text-secondary)] text-center">No tool activity</div>}
          </div>
        </div>
      </div>
    </div>
  )
}
