import {
  Activity,
  Clock,
  Box,
  Terminal,
  Pause,
  Play,
  RotateCcw,
  X,
  AlertCircle,
  Loader2,
  type LucideIcon,
} from 'lucide-react'
import { formatTokens, formatUsd } from '../lib/utils'
import type { LivePanel } from '../hooks/useLivePanels'
import { useLivePanelConnection, type ConnectionState } from '../hooks/useLivePanelConnection'

type Props = {
  panel: LivePanel
  sourceScope: string
  globalPaused: boolean
  onRemove: () => void
  animationDelay?: number
}

export default function LivePanel({ panel, sourceScope, globalPaused, onRemove, animationDelay = 0 }: Props) {
  const { data, streamMode, reconnectCountdown, isPaused, pause, resume, refresh, isLoading, isError } = useLivePanelConnection(
    panel.sessionId,
    sourceScope,
    globalPaused
  )

  const statusConfig: Record<ConnectionState, { label: string; icon?: LucideIcon }> = {
    connecting: {
      label: 'Connecting...',
      icon: Loader2,
    },
    streaming: {
      label: 'Live',
    },
    polling: {
      label: reconnectCountdown !== null ? `Reconnecting in ${reconnectCountdown}s` : 'Polling',
    },
    paused: {
      label: 'Paused',
    },
    error: {
      label: 'Error',
      icon: AlertCircle,
    },
  }
  const effectiveMode: ConnectionState = isPaused ? 'paused' : streamMode
  const status = statusConfig[effectiveMode]

  if (isError) {
    return (
      <div
        className="ds-surface p-6 animate-slide-up"
        style={{ animationDelay: `${animationDelay}ms` }}
      >
        <div className="flex flex-col items-center justify-center gap-3 text-center">
          <div className="w-10 h-10 rounded-full bg-[var(--color-error-muted)] flex items-center justify-center">
            <AlertCircle className="w-5 h-5 text-[var(--color-error)]" />
          </div>
          <div>
            <p className="ds-text-body font-medium text-[var(--text-secondary)]">Unable to connect to session</p>
            <p className="ds-text-muted text-sm mt-0.5">{panel.sessionTitle || panel.sessionId}</p>
          </div>
          <div className="flex gap-2 mt-2">
            <button type="button" onClick={refresh} className="ds-btn-secondary">
              <RotateCcw className="w-4 h-4 mr-2" />
              Retry
            </button>
            <button
              type="button"
              onClick={onRemove}
              className="ds-btn-ghost text-[var(--color-error)]"
              aria-label="Remove panel"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    )
  }

  if (isLoading || !data) {
    return (
      <div
        className="ds-surface p-6 animate-slide-up"
        style={{ animationDelay: `${animationDelay}ms` }}
      >
        <div className="flex flex-col gap-3">
          <div className="h-3.5 w-24 rounded bg-[var(--surface-tertiary)]" />
          <div className="h-7 w-48 rounded bg-[var(--surface-secondary)]" />
          <div className="h-4 w-32 rounded bg-[var(--surface-tertiary)] mt-2" />
        </div>
      </div>
    )
  }

  const isActuallyActive = data.active_session?.is_active ?? false

  return (
    <div
      className="ds-surface flex flex-col p-4 transition-all duration-200 animate-slide-up"
      style={{ animationDelay: `${animationDelay}ms` }}
    >
      <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            <span className="relative flex h-2.5 w-2.5">
              {isActuallyActive && (
                <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-[var(--color-success)] opacity-75"></span>
              )}
              <span className={`relative inline-flex rounded-full h-2.5 w-2.5 ${
                isActuallyActive ? 'bg-[var(--color-success)]' : 'bg-[var(--surface-tertiary)]'
              }`}></span>
            </span>
            <span className="ds-text-subheading font-semibold text-[var(--text-primary)] truncate" title={panel.sessionTitle || panel.sessionId}>
              {panel.sessionTitle || panel.sessionId}
            </span>
          </div>
          {panel.projectName && (
            <div className="ds-text-mono text-xs text-[var(--text-tertiary)] truncate" title={panel.projectPath || panel.projectName}>
              {panel.projectName}
            </div>
          )}
        </div>
        <div className="shrink-0 flex items-center gap-1.5">
          <span className={`ds-badge ${effectiveMode === 'streaming' ? 'ds-badge-success' : 'ds-badge-default'} text-[10px] font-semibold px-2 py-0.5 rounded-full inline-flex items-center`}>
            {status.icon && <status.icon className="w-3 h-3 mr-1" />}
            {status.label}
          </span>
        </div>
      </div>

      {data.active_session && (
        <div
          className={`p-4 rounded-lg border transition-colors relative overflow-hidden ${
            isActuallyActive
              ? 'bg-[var(--surface-accent)] border-[var(--border-accent)]'
              : 'bg-[var(--surface-secondary)] border-[var(--border-subtle)]'
          }`}
        >
          {isActuallyActive && (
            <div className="absolute top-0 right-0 w-24 h-24 bg-[var(--accent-primary)] opacity-5 rounded-full blur-2xl transform translate-x-6 -translate-y-6 pointer-events-none" />
          )}
          <div className="flex items-center gap-2 text-sm font-semibold text-[var(--accent-primary-muted-foreground)] mb-1.5 relative z-10">
            <Activity className="w-3.5 h-3.5" />
            {isActuallyActive ? 'Active Session' : 'Last Session'}
          </div>
          <div className="ds-text-body text-[var(--text-primary)] truncate">
            {data.active_session.title || data.active_session.session_id}
          </div>
          <div className="ds-text-muted text-sm mt-1 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            Updated {new Date(data.active_session.last_updated_ms).toLocaleTimeString()}
          </div>
        </div>
      )}

      <div className="grid grid-cols-3 gap-2 pt-3 mt-auto border-t border-[var(--border-subtle)]">
        <div className="flex flex-col gap-0.5">
          <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Tokens</span>
          <span className="ds-text-tabular font-bold tabular-nums text-[var(--text-primary)] text-sm">
            {formatTokens(data.usage.total_tokens)}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Cost</span>
          <span className="ds-text-tabular font-bold tabular-nums text-[var(--text-primary)] text-sm">
            {data.cost_usd != null ? formatUsd(data.cost_usd) : '–'}
          </span>
        </div>
        <div className="flex flex-col gap-0.5">
          <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Interactions</span>
          <span className="ds-text-tabular font-bold tabular-nums text-[var(--text-primary)] text-sm">
            {data.total_interactions}
          </span>
        </div>
      </div>

      {(data.top_models?.length ?? 0) > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 ds-text-subheading text-[var(--text-primary)] mb-2">
            <Box className="w-3.5 h-3.5" />
            Models
          </div>
          <div className="flex flex-col gap-0.5">
            {data.top_models?.map((m) => (
              <div key={m.model_id} className="flex justify-between items-center gap-3 py-2 px-2.5 rounded-md hover:bg-[var(--surface-tertiary)]/50 transition-colors">
                <span className="ds-text-body text-[var(--text-secondary)] truncate text-sm font-medium" title={m.model_id}>
                  {m.model_id.split('/').pop() || m.model_id}
                </span>
                <span className="ds-text-tabular font-semibold text-[var(--text-primary)] tabular-nums text-sm">
                  {formatTokens(m.usage.total_tokens)}
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      {(data.top_tools?.length ?? 0) > 0 && (
        <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
          <div className="flex items-center gap-2 ds-text-subheading text-[var(--text-primary)] mb-2">
            <Terminal className="w-3.5 h-3.5" />
            Tools
          </div>
          <div className="flex flex-col gap-0.5">
            {data.top_tools?.map((t) => (
              <div key={t.tool_name} className="flex justify-between items-center gap-3 py-2 px-2.5 rounded-md hover:bg-[var(--surface-tertiary)]/50 transition-colors">
                <span className="ds-text-body text-[var(--text-secondary)] truncate text-sm font-medium">
                  {t.tool_name}
                </span>
                <span className="ds-text-tabular font-semibold text-[var(--text-secondary)] tabular-nums text-sm">
                  {t.total_calls} calls
                </span>
              </div>
            ))}
          </div>
        </div>
      )}

      <div className="mt-auto pt-3 border-t border-[var(--border-subtle)] flex items-center justify-end gap-1 bg-[var(--surface-secondary)]/30 rounded-b-lg">
          <button
            type="button"
            onClick={isPaused ? resume : pause}
            className="ds-btn-ghost text-xs py-1.5 px-2 focus-ring"
            aria-label={isPaused ? 'Resume' : 'Pause'}
          >
          {isPaused ? <Play className="w-3 h-3" /> : <Pause className="w-3 h-3" />}
        </button>
        <button
          type="button"
          onClick={refresh}
          className="ds-btn-ghost text-xs py-1.5 px-2 focus-ring"
          aria-label="Refresh"
        >
          <RotateCcw className="w-3 h-3" />
        </button>
        <button
          type="button"
          onClick={onRemove}
          className="ds-btn-ghost text-xs py-1.5 px-2 text-[var(--color-error)] hover:bg-[var(--color-error-muted)] focus-ring"
          aria-label="Remove panel"
        >
          <X className="w-3 h-3" />
        </button>
      </div>
    </div>
  )
}
