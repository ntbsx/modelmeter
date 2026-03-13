const RANGE_OPTIONS = [
  { days: 1, label: '24h' },
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
  { days: 90, label: '90d' },
] as const

type TimeRangeFilterProps = {
  days: number
  onChange: (days: 1 | 7 | 30 | 90) => void
}

export default function TimeRangeFilter({ days, onChange }: TimeRangeFilterProps) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Window</span>

      <select
        aria-label="Select time range"
        className="sm:hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-2.5 py-1.5 text-xs text-gray-700 dark:text-gray-200"
        onChange={(event) => onChange(Number(event.target.value) as 1 | 7 | 30 | 90)}
        value={days}
      >
        {RANGE_OPTIONS.map((option) => (
          <option key={option.days} value={option.days}>
            {option.label}
          </option>
        ))}
      </select>

      <div className="hidden sm:inline-flex rounded-xl border border-gray-200 dark:border-gray-800 bg-white/90 dark:bg-gray-900/90 p-1 gap-1 shadow-sm">
        {RANGE_OPTIONS.map((option) => {
          const active = option.days === days
          return (
            <button
              key={option.days}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
              onClick={() => onChange(option.days)}
              type="button"
            >
              {option.label}
            </button>
          )
        })}
      </div>
    </div>
  )
}
