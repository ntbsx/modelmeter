import { useState, useRef, useEffect } from 'react'
import { Calendar } from 'lucide-react'

const PRESET_OPTIONS = [
  { days: 1, label: '24h' },
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
  { days: 90, label: '90d' },
] as const

type DateRangeFilterProps = {
  days: number
  onChange: (days: number) => void
}

export default function DateRangeFilter({ days, onChange }: DateRangeFilterProps) {
  const [showPicker, setShowPicker] = useState(false)
  const [customDays, setCustomDays] = useState<string>('')
  const pickerRef = useRef<HTMLDivElement>(null)

  // Check if current days matches a preset
  const isCustom = !PRESET_OPTIONS.some((opt) => opt.days === days)

  // Close picker when clicking outside
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (pickerRef.current && !pickerRef.current.contains(event.target as Node)) {
        setShowPicker(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handlePresetClick = (presetDays: number) => {
    setShowPicker(false)
    setCustomDays('')
    onChange(presetDays)
  }

  const handleCustomClick = () => {
    setShowPicker(true)
    setCustomDays(isCustom ? String(days) : '')
  }

  const handleApplyCustomDays = () => {
    const parsed = parseInt(customDays, 10)
    if (!isNaN(parsed) && parsed >= 1) {
      setShowPicker(false)
      onChange(parsed)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleApplyCustomDays()
    }
  }

  // Format the custom label
  const customLabel = isCustom ? `${days}d` : 'Custom'

  return (
    <div className="flex items-center gap-2 relative" ref={pickerRef}>
      <span className="text-xs uppercase tracking-wide text-gray-500 dark:text-gray-400">Window</span>

      {/* Mobile select */}
      <select
        aria-label="Select time range"
        className="sm:hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-2.5 py-1.5 text-xs text-gray-700 dark:text-gray-200"
        onChange={(event) => {
          const value = event.target.value
          if (value === 'custom') {
            handleCustomClick()
          } else {
            handlePresetClick(Number(value))
          }
        }}
        value={isCustom ? 'custom' : days}
      >
        {PRESET_OPTIONS.map((option) => (
          <option key={option.days} value={option.days}>
            {option.label}
          </option>
        ))}
        <option value="custom">Custom...</option>
      </select>

      {/* Desktop buttons */}
      <div className="hidden sm:inline-flex rounded-xl border border-gray-200 dark:border-gray-800 bg-white/90 dark:bg-gray-900/90 p-1 gap-1 shadow-sm">
        {PRESET_OPTIONS.map((option) => {
          const active = option.days === days
          return (
            <button
              key={option.days}
              className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                active
                  ? 'bg-blue-600 text-white'
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
              }`}
              onClick={() => handlePresetClick(option.days)}
              type="button"
            >
              {option.label}
            </button>
          )
        })}
        <button
          className={`px-3 py-1.5 text-xs rounded-lg font-medium transition-colors inline-flex items-center gap-1.5 ${
            isCustom
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
          onClick={handleCustomClick}
          type="button"
        >
          <Calendar className="w-3.5 h-3.5" />
          {customLabel}
        </button>
      </div>

      {/* Custom days picker dropdown */}
      {showPicker && (
        <div className="absolute top-full right-0 mt-2 z-50 bg-white dark:bg-gray-900 border border-gray-200 dark:border-gray-800 rounded-xl shadow-lg p-4 min-w-[200px]">
          <div className="space-y-3">
            <div className="text-sm font-medium text-gray-900 dark:text-white">
              Custom Time Window
            </div>
            <div>
              <label htmlFor="custom-days-input" className="block text-xs text-gray-500 dark:text-gray-400 mb-1">
                Number of days
              </label>
              <input
                id="custom-days-input"
                type="number"
                min="1"
                max="365"
                value={customDays}
                onChange={(e) => setCustomDays(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="e.g. 14"
                className="w-full rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2 text-sm text-gray-700 dark:text-gray-200 outline-none focus:ring-2 focus:ring-blue-500/40"
                autoFocus
              />
              <p className="text-xs text-gray-400 dark:text-gray-500 mt-1">
                Shows data from the last N days
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowPicker(false)}
                className="px-3 py-2 text-xs rounded-lg font-medium text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplyCustomDays}
                disabled={!customDays || parseInt(customDays, 10) < 1}
                className="px-4 py-2 text-xs rounded-lg font-medium bg-blue-600 text-white hover:bg-blue-700 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Apply
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
