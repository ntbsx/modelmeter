type Props = {
  sourceScope?: string | null
  sourcesConsidered?: string[]
  sourcesSucceeded?: string[]
  sourcesFailed?: Array<{ source_id: string; error: string }>
}

function scopeLabel(scope: string | null | undefined): string {
  if (!scope || scope === 'local') return 'Local'
  if (scope === 'all') return 'All Sources'
  return scope
}

export default function SourceMetaBanner({
  sourceScope,
  sourcesConsidered = [],
  sourcesSucceeded = [],
  sourcesFailed = [],
}: Props) {
  return (
    <div className="mb-4 rounded-lg border border-gray-200 dark:border-gray-800 bg-gray-50/70 dark:bg-gray-900/50 px-3 py-2 text-xs text-gray-600 dark:text-gray-300">
      <div className="flex flex-wrap items-center gap-2">
        <span className="inline-flex rounded-full bg-blue-50 text-blue-700 dark:bg-blue-900/40 dark:text-blue-300 px-2 py-0.5 font-medium">
          Scope: {scopeLabel(sourceScope)}
        </span>
        <span>Considered: {sourcesConsidered.length}</span>
        <span>Succeeded: {sourcesSucceeded.length}</span>
        <span className={sourcesFailed.length > 0 ? 'text-amber-700 dark:text-amber-300' : ''}>
          Failed: {sourcesFailed.length}
        </span>
      </div>
      {sourcesFailed.length > 0 ? (
        <div className="mt-1 text-amber-700 dark:text-amber-300">
          {sourcesFailed.map((failure) => `${failure.source_id}: ${failure.error}`).join(' | ')}
        </div>
      ) : null}
    </div>
  )
}
