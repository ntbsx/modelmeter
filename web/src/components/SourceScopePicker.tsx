import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import type { SourceRegistryPublic } from '../types'
import { useSourceScope, type SourceScopeValue } from '../hooks/useSourceScope'

export default function SourceScopePicker() {
  const { sourceScope, setSourceScope } = useSourceScope()
  const { data } = useQuery<SourceRegistryPublic>({
    queryKey: ['sources-registry'],
    queryFn: () => fetchApi('/sources'),
    staleTime: 15_000,
  })

  const enabledSources = useMemo(
    () => (data?.sources ?? []).filter((s) => s.enabled),
    [data?.sources]
  )

  const hasMultipleSources = enabledSources.length > 0

  const options = useMemo(() => {
    const base: Array<{ value: SourceScopeValue; label: string; group: string }> = [
      { value: 'self', label: 'This Server', group: 'Local' },
    ]

    if (hasMultipleSources) {
      base.push({ value: 'all', label: 'All Sources', group: 'Local' })
    }

    const specific = enabledSources.map((source) => ({
      value: `source:${source.source_id}` as SourceScopeValue,
      label: source.label || source.source_id,
      group: 'Remote',
    }))

    return [...base, ...specific]
  }, [enabledSources, hasMultipleSources])

  if (!hasMultipleSources) {
    return (
      <span className="inline-flex rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-2.5 py-1.5 text-xs font-medium">
        🏠 This Server
      </span>
    )
  }

  return (
    <div className="relative inline-block">
      <select
        id="source-scope-picker"
        value={sourceScope}
        onChange={(event) => setSourceScope(event.target.value as SourceScopeValue)}
        className="appearance-none rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-950 pl-3 pr-8 py-1.5 text-xs text-gray-700 dark:text-gray-200 font-medium cursor-pointer hover:border-gray-300 dark:hover:border-gray-600 focus:outline-none focus:ring-2 focus:ring-blue-500/50"
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.group === 'Local' ? '🏠 ' : '🌐 '}{option.label}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-2">
        <svg className="h-3 w-3 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  )
}
