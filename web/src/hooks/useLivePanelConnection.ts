import { useState, useEffect, useRef, useCallback } from 'react'
import { useQuery } from '@tanstack/react-query'
import { buildApiUrl, fetchApi, getAuthToken } from '../lib/api'
import type { LiveSnapshotResponse } from '../types'

export type ConnectionState = 'connecting' | 'streaming' | 'polling' | 'paused' | 'error'

interface UseLivePanelConnectionResult {
  data: LiveSnapshotResponse | null
  streamMode: ConnectionState
  reconnectCountdown: number | null
  isPaused: boolean
  pause: () => void
  resume: () => void
  refresh: () => void
  isLoading: boolean
  isError: boolean
}

export function useLivePanelConnection(
  sessionId: string,
  sourceScope: string,
  globalPaused: boolean
): UseLivePanelConnectionResult {
  const [streamData, setStreamData] = useState<LiveSnapshotResponse | null>(null)
  const [localPaused, setLocalPaused] = useState(false)
  const [streamMode, setStreamMode] = useState<ConnectionState>(() =>
    typeof window !== 'undefined' && typeof window.EventSource !== 'undefined'
      ? 'connecting'
      : 'polling'
  )
  const [reconnectCountdownSeconds, setReconnectCountdownSeconds] = useState<number | null>(null)
  const [reconnectAttempt, setReconnectAttempt] = useState(0)

  const eventSourceRef = useRef<EventSource | null>(null)

  const liveScope = sourceScope === 'self' ? sourceScope : 'self'

  // Polling fallback
  const { data: polledData, isError: pollingError, refetch } = useQuery<LiveSnapshotResponse>({
    queryKey: ['live-panel', sessionId, liveScope],
    queryFn: () => fetchApi(`/live/session/${sessionId}`, {
      window_minutes: 60,
      source_scope: liveScope,
    }),
    refetchInterval: 3000,
    enabled: streamMode === 'polling' && !localPaused && !globalPaused,
  })

  // SSE connection
  useEffect(() => {
    const isPaused = localPaused || globalPaused
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
      eventsParams._auth = authToken
    }

    const eventsUrl = buildApiUrl(`/live/session/${sessionId}/events`, eventsParams)
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
    eventSourceRef.current = source

    return () => {
      source.removeEventListener('live.snapshot', onSnapshot as EventListener)
      source.removeEventListener('live.error', onError)
      source.close()
      eventSourceRef.current = null
    }
  }, [localPaused, globalPaused, reconnectAttempt, liveScope, streamMode, sessionId])

  // Reconnect countdown
  useEffect(() => {
    const isPaused = localPaused || globalPaused
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
        if (value === null) return null
        return Math.max(0, value - 1)
      })
    }, 1000)

    return () => window.clearTimeout(timer)
  }, [localPaused, globalPaused, reconnectCountdownSeconds, streamMode])

  const pause = useCallback(() => setLocalPaused(true), [])
  const resume = useCallback(() => {
    setLocalPaused(false)
    setReconnectAttempt((value) => value + 1)
    setStreamMode('connecting')
  }, [])
  const refresh = useCallback(() => refetch(), [refetch])

  const data = streamData ?? polledData ?? null
  const isLoading = !data && streamMode !== 'error'
  const isError = streamMode === 'error' || pollingError

  return {
    data,
    streamMode,
    reconnectCountdown: reconnectCountdownSeconds,
    isPaused: localPaused || globalPaused,
    pause,
    resume,
    refresh,
    isLoading,
    isError,
  }
}
