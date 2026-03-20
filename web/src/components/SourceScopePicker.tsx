import { useMemo } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Globe2, House } from 'lucide-react'
import { fetchApi } from '../lib/api'
import type { SourceRegistryPublic } from '../types'
import { useSourceScope, type SourceScopeValue } from '../hooks/useSourceScope'

type Props = {
  compact?: boolean
}

export default function SourceScopePicker({ compact = false }: Props) {
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
    if (compact) {
      return (
        <div className="flex flex-1 flex-col items-center justify-center gap-0.5 px-1 py-2 rounded-lg text-[var(--text-tertiary)]">
          <House className="w-5 h-5" aria-hidden="true" />
          <span className="text-[10px] font-medium">Scope</span>
        </div>
      )
    }

    return (
      <span className="inline-flex items-center gap-1 text-[var(--text-tertiary)]">
        <span className="text-base">🏠</span>
        <span className={`font-medium ${compact ? 'text-[10px]' : 'text-xs'}`}>This Server</span>
      </span>
    )
  }

  if (compact) {
    return (
      <div className="relative flex flex-1 flex-col items-center justify-center gap-0.5 px-1 py-2 rounded-lg text-[var(--text-tertiary)] hover:text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)]/50">
        <Globe2 className="w-5 h-5" aria-hidden="true" />
        <span className="text-[10px] font-medium">Scope</span>
        <select
          id="source-scope-picker"
          aria-label="Source scope"
          value={sourceScope}
          onChange={(event) => setSourceScope(event.target.value as SourceScopeValue)}
          className="absolute inset-0 h-full w-full cursor-pointer opacity-0 focus-ring"
        >
          {options.map((option) => (
            <option key={option.value} value={option.value}>
              {option.group === 'Local' ? '🏠 ' : '🌐 '}{option.label}
            </option>
          ))}
        </select>
      </div>
    )
  }

  return (
    <div className="relative inline-block">
      <select
        id="source-scope-picker"
        aria-label="Source scope"
        value={sourceScope}
        onChange={(event) => setSourceScope(event.target.value as SourceScopeValue)}
        className={`appearance-none rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] ${compact ? 'pl-1.5 pr-5 py-1 text-[10px]' : 'pl-3 pr-8 py-1.5 text-xs'} text-[var(--text-primary)] font-medium cursor-pointer hover:border-[var(--border-strong)] focus:outline-none focus:ring-2 focus:ring-[var(--accent-primary)]/50`}
      >
        {options.map((option) => (
          <option key={option.value} value={option.value}>
            {option.group === 'Local' ? '🏠 ' : '🌐 '}{option.label}
          </option>
        ))}
      </select>
      <div className="pointer-events-none absolute inset-y-0 right-0 flex items-center px-1.5">
        <svg className={`${compact ? 'h-2.5 w-2.5' : 'h-3 w-3'} text-[var(--text-tertiary)]`} fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </div>
    </div>
  )
}
