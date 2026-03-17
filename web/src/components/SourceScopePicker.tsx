import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import type { SourceRegistryPublic } from '../types'
import { useSourceScope, type SourceScopeValue } from '../hooks/useSourceScope'

function labelFromScope(scope: SourceScopeValue): string {
  if (scope === 'local') return 'Local'
  if (scope === 'all') return 'All Sources'
  return scope
}

export default function SourceScopePicker() {
  const { sourceScope, setSourceScope } = useSourceScope()
  const { data } = useQuery<SourceRegistryPublic>({
    queryKey: ['sources-registry'],
    queryFn: () => fetchApi('/sources'),
    staleTime: 15_000,
  })

  const options = useMemo(() => {
    const base: Array<{ value: SourceScopeValue; label: string }> = [
      { value: 'local', label: 'Local' },
      { value: 'all', label: 'All Sources' },
    ]

    const specific = (data?.sources ?? [])
      .filter((source) => source.enabled)
      .map((source) => ({
        value: `source:${source.source_id}` as SourceScopeValue,
        label: source.label ? `${source.label} (${source.source_id})` : source.source_id,
      }))

    return [...base, ...specific]
  }, [data?.sources])

  return (
    <div className="flex items-center gap-2">
      <label className="text-xs text-gray-500 dark:text-gray-400" htmlFor="source-scope-picker">
        Scope
      </label>
      <select
        id="source-scope-picker"
        value={sourceScope}
        onChange={(event) => setSourceScope(event.target.value as SourceScopeValue)}
        className="rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-950 px-2.5 py-1.5 text-xs text-gray-700 dark:text-gray-200"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      <span className="hidden sm:inline-flex rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-2 py-1 text-xs font-medium">
        {labelFromScope(sourceScope)}
      </span>
    </div>
  )
}
