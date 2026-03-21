import { Clock, Activity, CheckCircle2 } from 'lucide-react'
import { formatTokens, formatUsd } from '../lib/utils'
import type { components } from '../generated/api'

type SessionSummary = components['schemas']['SessionSummary']

type Props = {
  session: SessionSummary
  isAdded: boolean
  onSelect: () => void
  animationDelay?: number
}

export default function SessionCard({ session, isAdded, onSelect, animationDelay = 0 }: Props) {
  const isActive = session.is_active
  const updatedLabel = new Date(session.time_updated).toLocaleTimeString()

  return (
    <button
      type="button"
      onClick={isAdded ? undefined : onSelect}
      disabled={isAdded}
      className={`ds-surface flex flex-col p-4 transition-all duration-200 ${
        isAdded ? 'opacity-50 cursor-not-allowed' : 'hover:-translate-y-0.5 hover:shadow-md cursor-pointer'
      } animate-slide-up`}
      aria-label={session.title ? `Add session ${session.title}` : `Add session ${session.session_id}`}
      style={{
        borderTop: isActive ? `3px solid var(--color-success)` : `3px solid var(--border-default)`,
        animationDelay: `${animationDelay}ms`,
      }}
    >
      <div className="relative">
        <div className="flex items-start justify-between gap-2 mb-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-0.5">
            {isActive && (
              <span className="inline-flex items-center gap-1.5 ds-badge ds-badge-success text-[10px] font-semibold px-1.5 py-0.5 rounded-full">
                <Activity className="w-3 h-3" />
                Active
              </span>
            )}
            <span className="ds-text-subheading font-semibold text-[var(--text-primary)] truncate" title={session.title || session.session_id}>
              {session.title || session.session_id}
            </span>
          </div>
          {session.project_name && (
            <div className="ds-text-mono text-xs text-[var(--text-tertiary)] truncate" title={session.directory || session.project_name}>
              {session.project_name}
            </div>
          )}
        </div>
        <div className="shrink-0 flex flex-col items-end gap-1">
          <div className="flex items-center gap-1.5">
            <span className="ds-text-mono text-xs text-[var(--text-tertiary)]">
              {session.message_count} msg
            </span>
            {session.model_count > 0 && (
              <span className="ds-text-mono text-xs text-[var(--text-tertiary)]">
                {session.model_count} model{session.model_count !== 1 ? 's' : ''}
              </span>
            )}
          </div>
          <div className="flex items-center gap-1 text-[var(--text-tertiary)] text-xs">
            <Clock className="w-3 h-3" />
            Updated {updatedLabel}
          </div>
        </div>
      </div>

      <div className="grid grid-cols-3 gap-2 pt-3 mt-auto border-t border-[var(--border-subtle)]">
        <div className="flex flex-col gap-0.5">
          <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Tokens</span>
          <span className="ds-text-tabular font-bold tabular-nums text-[var(--text-primary)] text-sm">
            {formatTokens(session.token_count)}
          </span>
        </div>
        {session.cost_usd != null && (
          <div className="flex flex-col gap-0.5">
            <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Cost</span>
            <span className="ds-text-tabular font-bold tabular-nums text-[var(--color-success)] text-sm">
              {formatUsd(session.cost_usd)}
            </span>
          </div>
        )}
        <div className="flex flex-col gap-0.5">
          <span className="ds-text-label-uppercase text-[var(--text-tertiary)] text-[11px]">Models</span>
          <span className="ds-text-tabular font-bold tabular-nums text-[var(--text-primary)] text-sm">
            {session.model_count}
          </span>
        </div>
      </div>

      {isAdded && (
        <div className="absolute top-3 right-3">
          <CheckCircle2 className="w-5 h-5 text-[var(--color-success)]" />
        </div>
      )}
      </div>
    </button>
  )
}
