import { useState, useMemo, useEffect, useRef, useCallback } from 'react'
import { Search, X, Clock } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { LIVE_ACTIVITY_WINDOW_HOURS, LIVE_ACTIVITY_WINDOW_LABEL } from '../lib/liveWindow'
import type { components } from '../generated/api'
import SessionCard from './SessionCard'

type SessionSummary = components['schemas']['SessionSummary']

type Props = {
  isOpen: boolean
  onClose: () => void
  onSelectSession: (session: SessionSummary) => void
  excludeSessionIds: string[]
}

export default function SessionPicker({ isOpen, onClose, onSelectSession, excludeSessionIds }: Props) {
  const [searchQuery, setSearchQuery] = useState('')
  const previouslyFocusedRef = useRef<HTMLElement | null>(null)

  const handleClose = useCallback(() => {
    setSearchQuery('')
    onClose()
  }, [onClose])

  const { data, isLoading, error, refetch } = useQuery<SessionSummary[]>({
    queryKey: ['sessions-list', 'active-6h'],
    queryFn: () => {
      const params: Record<string, string | number | boolean> = {
        limit: 50,
        include_archived: false,
        active_since_hours: LIVE_ACTIVITY_WINDOW_HOURS,
      }
      return fetchApi<SessionSummary[]>('/sessions', params)
    },
    enabled: isOpen,
    staleTime: 30_000,
  })

  const filteredSessions = useMemo(() => {
    const sessions = data ?? []
    const query = searchQuery.toLowerCase().trim()

    if (!query) return sessions

    return sessions.filter((s) => {
      const matchesTitle = s.title?.toLowerCase().includes(query) ?? false
      const matchesSessionId = s.session_id.toLowerCase().includes(query)
      const matchesProject = s.project_name?.toLowerCase().includes(query) ?? false
      const matchesDirectory = s.directory?.toLowerCase().includes(query) ?? false
      return matchesTitle || matchesSessionId || matchesProject || matchesDirectory
    })
  }, [data, searchQuery])

  const availableSessions = useMemo(() => {
    return filteredSessions.filter((s) => !excludeSessionIds.includes(s.session_id))
  }, [filteredSessions, excludeSessionIds])

  useEffect(() => {
    if (!isOpen) {
      return
    }

    previouslyFocusedRef.current = document.activeElement as HTMLElement | null

    const onKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') {
        handleClose()
        return
      }

      if (event.key !== 'Tab') {
        return
      }

      const dialog = document.querySelector<HTMLElement>('[role="dialog"][aria-modal="true"]')
      if (!dialog) {
        return
      }

      const focusable = dialog.querySelectorAll<HTMLElement>(
        'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
      )
      if (focusable.length === 0) {
        return
      }

      const first = focusable[0]
      const last = focusable[focusable.length - 1]
      const active = document.activeElement as HTMLElement | null

      if (event.shiftKey && active === first) {
        event.preventDefault()
        last.focus()
      } else if (!event.shiftKey && active === last) {
        event.preventDefault()
        first.focus()
      }
    }

    window.addEventListener('keydown', onKeyDown)
    return () => {
      window.removeEventListener('keydown', onKeyDown)
      previouslyFocusedRef.current?.focus()
    }
  }, [isOpen, handleClose])

  const handleSelectSession = (session: SessionSummary) => {
    onSelectSession(session)
    handleClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50" onClick={handleClose}>
      <div
        className="bg-[var(--surface-primary)] rounded-xl shadow-xl max-w-4xl w-full mx-4 flex flex-col max-h-[80vh]"
        role="dialog"
        aria-modal="true"
        aria-labelledby="live-session-picker-title"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-center justify-between p-5 border-b border-[var(--border-subtle)]">
          <div>
            <h2 id="live-session-picker-title" className="ds-text-heading text-[var(--text-primary)]">Add Live Session Panel</h2>
            <p className="ds-text-muted text-sm mt-0.5">
              Select a session to monitor in real-time
            </p>
          </div>
            <button
              type="button"
              onClick={handleClose}
              className="ds-btn-ghost"
              aria-label="Close"
            >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 border-b border-[var(--border-subtle)]">
          <div className="relative mb-3">
            <label htmlFor="live-session-search" className="sr-only">
              Search sessions
            </label>
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)]" />
            <input
              id="live-session-search"
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              autoFocus
              placeholder="Search by session name, project, or ID..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] text-sm text-[var(--text-primary)]"
            />
          </div>
          <div className="flex items-center justify-between gap-2 text-sm text-[var(--text-secondary)]">
            <div className="flex items-center gap-2">
            <Clock className="w-4 h-4" />
            <span>{`Showing sessions active in the last ${LIVE_ACTIVITY_WINDOW_LABEL}`}</span>
            </div>
            <button type="button" onClick={() => refetch()} className="ds-btn-ghost text-xs">
              Refresh
            </button>
          </div>
        </div>

        <div className="flex-1 overflow-y-auto p-4">
          {isLoading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-2 border-[var(--accent-primary)] border-t-transparent" />
            </div>
          ) : error ? (
            <div className="flex flex-col items-center justify-center py-8 gap-3 text-center">
              <div className="w-10 h-10 rounded-full bg-[var(--color-error-muted)] flex items-center justify-center">
                <X className="w-5 h-5 text-[var(--color-error)]" />
              </div>
              <div>
                <p className="ds-text-body font-medium text-[var(--text-secondary)]">Failed to load sessions</p>
                <p className="ds-text-muted text-sm mt-0.5">Please try again</p>
              </div>
            </div>
          ) : availableSessions.length === 0 ? (
            <div className="ds-surface flex flex-col items-center justify-center py-12 gap-3 text-center">
              <div className="w-10 h-10 rounded-full bg-[var(--surface-tertiary)] flex items-center justify-center">
                <Search className="w-5 h-5 text-[var(--text-tertiary)]" />
              </div>
              <div>
                <p className="ds-text-body font-medium text-[var(--text-secondary)]">No sessions found</p>
                <p className="ds-text-muted text-sm mt-0.5">
                  {filteredSessions.length === 0
                    ? 'Try adjusting your search'
                    : 'All available sessions are already in use'}
                </p>
              </div>
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {availableSessions.map((session, i) => (
                <SessionCard
                  key={session.session_id}
                  session={session}
                  isAdded={false}
                  onSelect={() => handleSelectSession(session)}
                  animationDelay={Math.min(i, 4) * 50}
                />
              ))}
            </div>
          )}
        </div>

        <div className="p-4 border-t border-[var(--border-subtle)] flex items-center justify-between bg-[var(--surface-secondary)]/30 rounded-b-xl">
          <p className="ds-text-muted text-sm">
            {availableSessions.length} session{availableSessions.length !== 1 ? 's' : ''} available
          </p>
          <div className="flex gap-2">
            <button type="button" onClick={handleClose} className="ds-btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
