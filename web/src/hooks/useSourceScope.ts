import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

export type SourceScopeValue = 'local' | 'all' | `source:${string}`

function normalizeScope(raw: string | null): SourceScopeValue {
  if (raw === 'all') return 'all'
  if (raw && raw.startsWith('source:') && raw.length > 'source:'.length) {
    return raw as SourceScopeValue
  }
  return 'local'
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
  }

  return { sourceScope, setSourceScope }
}
