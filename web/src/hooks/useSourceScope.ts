import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export type SourceScopeValue = 'self' | 'all' | `source:${string}`

const LOCAL_STORAGE_KEY = 'modelmeter_source_scope'

function getStoredScope(): SourceScopeValue {
  try {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY)
    if (stored === 'all' || stored === 'self') return stored
    if (stored && stored.startsWith('source:') && stored.length > 'source:'.length) {
      return stored as SourceScopeValue
    }
  } catch {
    // localStorage not available
  }
  return 'self'
}

function setStoredScope(scope: SourceScopeValue): void {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, scope)
  } catch {
    // localStorage not available
  }
}

function normalizeScope(raw: string | null): SourceScopeValue {
  if (raw === 'all') return 'all'
  if (raw && raw.startsWith('source:') && raw.length > 'source:'.length) {
    return raw as SourceScopeValue
  }
  if (raw === null) {
    return getStoredScope()
  }
  return 'self'
}

export function useSourceScope() {
  const [searchParams, setSearchParams] = useSearchParams()

  const sourceScope = useMemo(
    () => normalizeScope(searchParams.get('source_scope')),
    [searchParams]
  )

  const setSourceScope = (next: SourceScopeValue) => {
    const params = new URLSearchParams(searchParams)
    params.set('source_scope', next)
    setSearchParams(params, { replace: true })
    setStoredScope(next)
  }

  return { sourceScope, setSourceScope }
}
