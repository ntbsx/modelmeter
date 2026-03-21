import { useMemo, useState } from 'react'
import { Plus, Pause, Play } from 'lucide-react'
import { useLivePanels, type LivePanel as LivePanelType } from '../hooks/useLivePanels'
import { useSourceScope } from '../hooks/useSourceScope'
import LivePanel from '../components/LivePanel'
import SessionPicker from '../components/SessionPicker'
import { PageHeader } from '../components/DataTable'
import type { components } from '../generated/api'

type SessionSummary = components['schemas']['SessionSummary']

export default function Live() {
  const { panels, addPanel, removePanel, maxPanels, reachedMax, panelCount } = useLivePanels()
  const { sourceScope } = useSourceScope()
  const [isPickerOpen, setIsPickerOpen] = useState(false)
  const [globalPaused, setGlobalPaused] = useState(false)

  const handleToggleGlobalPause = () => {
    setGlobalPaused((prev) => !prev)
  }

  const handleAddPanel = (session: SessionSummary) => {
    const result = addPanel({
      session_id: session.session_id,
      title: session.title ?? null,
      project_name: session.project_name ?? null,
      directory: session.directory ?? null,
    })
    if (!result.success) {
      console.error(result.reason)
    }
  }

  const handleRemovePanel = (panelId: string) => {
    removePanel(panelId)
  }

  const sortedPanels = useMemo(() => {
    return [...panels].sort((a, b) => a.position - b.position)
  }, [panels])

  const gridColumns = useMemo(() => {
    if (panelCount === 1) return 'grid-cols-1'
    if (panelCount === 2) return 'md:grid-cols-2'
    if (panelCount <= 4) return 'lg:grid-cols-2 xl:grid-cols-3'
    return 'lg:grid-cols-2 xl:grid-cols-3'
  }, [panelCount])

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto w-full min-w-0 space-y-6">
      <PageHeader
        title="Live Monitoring"
        description="Monitor multiple sessions in real-time"
        actions={
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={handleToggleGlobalPause}
              className="ds-btn-secondary"
              title={globalPaused ? 'Resume all' : 'Pause all'}
            >
              {globalPaused ? <Play className="w-4 h-4 mr-2" /> : <Pause className="w-4 h-4 mr-2" />}
              {globalPaused ? 'Resume All' : 'Pause All'}
            </button>
            <button
              type="button"
              onClick={() => setIsPickerOpen(true)}
              disabled={reachedMax}
              className="ds-btn-primary"
              title={reachedMax ? `Maximum ${maxPanels} panels reached` : 'Add panel'}
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Panel
            </button>
          </div>
        }
      />

      <div className="ds-surface p-4 flex items-center gap-2 text-sm">
        <span className="ds-text-muted">
          Data source: This Server (self)
        </span>
        <span className="ds-text-muted text-xs">
          Multi-server monitoring coming soon
        </span>
      </div>

      {panelCount === 0 && (
        <div className="ds-surface flex flex-col items-center justify-center py-16 gap-3 text-center">
          <div className="w-12 h-12 rounded-full bg-[var(--surface-tertiary)] flex items-center justify-center">
            <Plus className="w-6 h-6 text-[var(--text-tertiary)]" />
          </div>
          <div>
            <p className="ds-text-body font-medium text-[var(--text-secondary)]">No live panels configured</p>
            <p className="ds-text-muted text-sm mt-0.5">
              Click "Add Panel" to start monitoring sessions
            </p>
          </div>
        </div>
      )}

      {panelCount > 0 && (
        <div className={`grid gap-4 sm:gap-5 ${gridColumns}`}>
          {sortedPanels.map((panel, i) => (
            <LivePanel
              key={panel.id}
              panel={panel}
              sourceScope={sourceScope}
              globalPaused={globalPaused}
              onToggleGlobalPause={handleToggleGlobalPause}
              onRemove={() => handleRemovePanel(panel.id)}
              animationDelay={Math.min(i, 4) * 50}
            />
          ))}
        </div>
      )}

      <SessionPicker
        isOpen={isPickerOpen}
        onClose={() => setIsPickerOpen(false)}
        onSelectSession={handleAddPanel}
        excludeSessionIds={panels.map((p: LivePanelType) => p.sessionId)}
      />
    </div>
  )
}
