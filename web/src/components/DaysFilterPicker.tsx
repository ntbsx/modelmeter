import { useState, useRef, useEffect } from 'react'
import { Calendar } from 'lucide-react'
import { useDaysFilter } from '../hooks/useDaysFilter'

const PRESET_OPTIONS = [
  { days: 1, label: '1d' },
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
] as const

export default function DaysFilterPicker() {
  const { days, setDays } = useDaysFilter()
  const [showPicker, setShowPicker] = useState(false)
  const [customDays, setCustomDays] = useState('')
  const pickerRef = useRef<HTMLDivElement>(null)

  const isCustom = !PRESET_OPTIONS.some((opt) => opt.days === days)

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
    setDays(presetDays)
  }

  const handleCustomClick = () => {
    setShowPicker(true)
    setCustomDays(isCustom ? String(days) : '')
  }

  const handleApplyCustomDays = () => {
    const parsed = parseInt(customDays, 10)
    if (!isNaN(parsed) && parsed >= 1) {
      setShowPicker(false)
      setDays(parsed)
    }
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleApplyCustomDays()
    } else if (e.key === 'Escape') {
      setShowPicker(false)
    }
  }

  const displayLabel = isCustom ? `${days}d` : `${days}d`

  return (
    <div className="relative" ref={pickerRef}>
      <div className="hidden sm:inline-flex rounded-xl border border-gray-200 dark:border-gray-800 bg-white/90 dark:bg-gray-900/90 p-0.5 gap-0.5 shadow-sm">
        {PRESET_OPTIONS.map((option) => {
          const active = option.days === days && !isCustom
          return (
            <button
              key={option.days}
              className={`px-2.5 py-1.5 text-xs rounded-lg font-medium transition-colors ${
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
          className={`px-2.5 py-1.5 text-xs rounded-lg font-medium transition-colors inline-flex items-center gap-1 ${
            isCustom
              ? 'bg-blue-600 text-white'
              : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800'
          }`}
          onClick={handleCustomClick}
          type="button"
        >
          <Calendar className="w-3 h-3" />
          {displayLabel}
        </button>
      </div>

      <select
        aria-label="Select time range"
        className="sm:hidden rounded-lg border border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-900 px-2 py-1.5 text-xs text-gray-700 dark:text-gray-200"
        onChange={(event) => {
          const value = event.target.value
          if (value === 'custom') {
            handleCustomClick()
          } else {
            setDays(Number(value))
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
