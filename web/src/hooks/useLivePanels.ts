import { useState, useEffect, useCallback } from 'react'

export interface LivePanel {
  id: string
  sessionId: string
  sessionTitle: string | null
  projectName: string | null
  projectPath: string | null
  position: number
  addedAt: number
}

const STORAGE_KEY = 'modelmeter_live_panels'
const MAX_PANELS = 6

function getStoredPanels(): LivePanel[] {
  try {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? JSON.parse(stored) : []
  } catch {
    return []
  }
}

function setStoredPanels(panels: LivePanel[]): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(panels))
  } catch {
    // ignore storage errors
  }
}

interface AddPanelResult {
  success: boolean
  reason?: string
}

export function useLivePanels() {
  const [panels, setPanels] = useState<LivePanel[]>(() => getStoredPanels())

  useEffect(() => {
    setStoredPanels(panels)
  }, [panels])

  const addPanel = useCallback((sessionSummary: { session_id: string; title: string | null; project_name: string | null; directory: string | null }): AddPanelResult => {
    // Fast path checks using current state for immediate user feedback
    if (panels.length >= MAX_PANELS) {
      return { success: false, reason: 'max-panels' }
    }

    if (panels.some((p) => p.sessionId === sessionSummary.session_id)) {
      return { success: false, reason: 'duplicate-session' }
    }

    setPanels((prev) => {
      // Re-enforce constraints against the latest state to handle concurrent adds
      if (prev.length >= MAX_PANELS) {
        return prev
      }
      if (prev.some((p) => p.sessionId === sessionSummary.session_id)) {
        return prev
      }

      const newPanel: LivePanel = {
        id: crypto.randomUUID(),
        sessionId: sessionSummary.session_id,
        sessionTitle: sessionSummary.title,
        projectName: sessionSummary.project_name,
        projectPath: sessionSummary.directory,
        position: prev.length,
        addedAt: Date.now(),
      }

      return [...prev, newPanel]
    })
    return { success: true }
  }, [panels])

  const removePanel = useCallback((panelId: string) => {
    setPanels((prev) => {
      const next = prev.filter((p) => p.id !== panelId)
      // Reorder remaining panels
      return next.map((p, i) => ({ ...p, position: i }))
    })
  }, [])

  return {
    panels,
    addPanel,
    removePanel,
    maxPanels: MAX_PANELS,
    reachedMax: panels.length >= MAX_PANELS,
    panelCount: panels.length,
  }
}
