import { useState, useMemo, useEffect } from 'react'
import { Search, X } from 'lucide-react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
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
  const { data, isLoading, error } = useQuery<SessionSummary[]>({
    queryKey: ['sessions-list'],
    queryFn: () => fetchApi<SessionSummary[]>('/sessions', { limit: 50, include_archived: false ? 1 : 0 }),
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
    if (!isOpen) setSearchQuery('')
  }, [isOpen])

  const handleSelectSession = (session: SessionSummary) => {
    onSelectSession(session)
    onClose()
  }

  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-[var(--surface-primary)] rounded-xl shadow-xl max-w-4xl w-full mx-4 flex flex-col max-h-[80vh]">
        <div className="flex items-center justify-between p-5 border-b border-[var(--border-subtle)]">
          <div>
            <h2 className="ds-text-heading text-[var(--text-primary)]">Add Live Session Panel</h2>
            <p className="ds-text-muted text-sm mt-0.5">
              Select a session to monitor in real-time
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="ds-btn-ghost"
            aria-label="Close"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-4 border-b border-[var(--border-subtle)]">
          <div className="relative">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-[var(--text-tertiary)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search by session name, project, or ID..."
              className="w-full pl-10 pr-4 py-2 rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] text-sm text-[var(--text-primary)]"
            />
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
            <button type="button" onClick={onClose} className="ds-btn-secondary">
              Cancel
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
