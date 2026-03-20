import { useState, useRef, useEffect } from 'react'
import { Calendar } from 'lucide-react'
import { useDaysFilter } from '../hooks/useDaysFilter'

const PRESET_OPTIONS = [
  { days: 1, label: '1d' },
  { days: 7, label: '7d' },
  { days: 30, label: '30d' },
] as const

type DaysFilterPickerProps = {
  scope?: string
}

export default function DaysFilterPicker({ scope }: DaysFilterPickerProps) {
  const { days, setDays } = useDaysFilter(scope)
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
      <div className="hidden sm:inline-flex rounded-xl border border-[var(--border-default)] bg-[var(--surface-primary)]/90 p-0.5 gap-0.5 shadow-sm">
        {PRESET_OPTIONS.map((option) => {
          const active = option.days === days && !isCustom
          return (
            <button
              key={option.days}
              className={`px-2.5 py-1.5 text-xs rounded-lg font-medium transition-colors ${
                active
                  ? 'bg-[var(--accent-primary)] text-[var(--text-inverse)]'
                  : 'text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)]'
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
              ? 'bg-[var(--accent-primary)] text-[var(--text-inverse)]'
              : 'text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)]'
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
        className="sm:hidden rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-2 py-1.5 text-xs text-[var(--text-primary)]"
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
        <div className="absolute top-full right-0 mt-2 z-50 bg-[var(--surface-primary)] border border-[var(--border-default)] rounded-xl shadow-lg p-4 min-w-[200px]">
          <div className="space-y-3">
            <div className="text-sm font-medium text-[var(--text-primary)]">
              Custom Time Window
            </div>
            <div>
              <label htmlFor="custom-days-input" className="block text-xs text-[var(--text-tertiary)] mb-1">
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
                className="w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)] outline-none focus:ring-2 focus:ring-[var(--accent-primary)]/40"
                autoFocus
              />
              <p className="text-xs text-[var(--text-tertiary)] mt-1">
                Shows data from the last N days
              </p>
            </div>
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={() => setShowPicker(false)}
                className="px-3 py-2 text-xs rounded-lg font-medium text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)] transition-colors"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleApplyCustomDays}
                disabled={!customDays || parseInt(customDays, 10) < 1}
                className="px-4 py-2 text-xs rounded-lg font-medium bg-[var(--accent-primary)] text-[var(--text-inverse)] hover:bg-[var(--accent-primary-hover)] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
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
