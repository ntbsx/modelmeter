import { useState } from 'react'
import { ChevronLeft, ChevronRight } from 'lucide-react'

type DatePickerProps = {
  value: string // YYYY-MM-DD
  onChange: (date: string) => void
  maxDate?: string
}

const DAY_LABELS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

function toLocalDateStr(year: number, month: number, day: number): string {
  return `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`
}

function parseYMD(dateStr: string): { year: number; month: number; day: number } | null {
  const parts = dateStr.split('-')
  if (parts.length !== 3) return null
  const year = parseInt(parts[0], 10)
  const month = parseInt(parts[1], 10) - 1
  const day = parseInt(parts[2], 10)
  if (isNaN(year) || isNaN(month) || isNaN(day)) return null
  return { year, month, day }
}

export default function DatePicker({ value, onChange, maxDate }: DatePickerProps) {
  const today = new Date()
  today.setHours(0, 0, 0, 0)

  const initial = parseYMD(value)
  const initialDate = initial ? new Date(initial.year, initial.month, initial.day) : today

  const [viewYear, setViewYear] = useState(initialDate.getFullYear())
  const [viewMonth, setViewMonth] = useState(initialDate.getMonth())

  const maxDateObj = maxDate ? parseYMD(maxDate) : null
  const maxDatejs = maxDateObj ? new Date(maxDateObj.year, maxDateObj.month, maxDateObj.day) : null

  const firstDayOfMonth = new Date(viewYear, viewMonth, 1)
  const lastDayOfMonth = new Date(viewYear, viewMonth + 1, 0)
  const startPad = firstDayOfMonth.getDay()
  const daysInMonth = lastDayOfMonth.getDate()

  const prevMonth = () => {
    if (viewMonth === 0) {
      setViewMonth(11)
      setViewYear((y) => y - 1)
    } else {
      setViewMonth((m) => m - 1)
    }
  }

  const nextMonth = () => {
    if (viewMonth === 11) {
      setViewMonth(0)
      setViewYear((y) => y + 1)
    } else {
      setViewMonth((m) => m + 1)
    }
  }

  const handleDayClick = (day: number) => {
    const dateStr = toLocalDateStr(viewYear, viewMonth, day)
    onChange(dateStr)
  }

  const cells: (number | null)[] = [
    ...Array(startPad).fill(null),
    ...Array.from({ length: daysInMonth }, (_, i) => i + 1),
  ]
  // pad to full weeks
  while (cells.length % 7 !== 0) cells.push(null)

  const monthName = firstDayOfMonth.toLocaleString('default', { month: 'long' })

  return (
    <div className="ds-surface border border-[var(--border-default)] rounded-xl shadow-lg p-4 w-[280px]">
      {/* header */}
      <div className="flex items-center justify-between mb-3">
        <button
          type="button"
          onClick={prevMonth}
          className="p-1 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)] transition-colors focus-ring"
        >
          <ChevronLeft className="w-4 h-4" aria-hidden="true" />
        </button>
        <span className="text-sm font-semibold text-[var(--text-primary)]">
          {monthName} {viewYear}
        </span>
        <button
          type="button"
          onClick={nextMonth}
          className="p-1 rounded-lg text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)] transition-colors focus-ring"
        >
          <ChevronRight className="w-4 h-4" aria-hidden="true" />
        </button>
      </div>

      {/* day labels */}
      <div className="grid grid-cols-7 mb-1">
        {DAY_LABELS.map((d) => (
          <div key={d} className="text-center text-xs font-medium text-[var(--text-tertiary)] py-1">
            {d}
          </div>
        ))}
      </div>

      {/* calendar grid */}
      <div className="grid grid-cols-7 gap-0.5">
        {cells.map((day, idx) => {
          if (day === null) {
            return <div key={`pad-${idx}`} />
          }
          const dateStr = toLocalDateStr(viewYear, viewMonth, day)
          const dateJs = new Date(viewYear, viewMonth, day)
          const isSelected = dateStr === value
          const isToday = dateJs.getTime() === today.getTime()
          const isFuture = maxDatejs && dateJs > maxDatejs

          return (
            <button
              key={day}
              type="button"
              onClick={() => !isFuture && handleDayClick(day)}
              disabled={!!isFuture}
              className={[
                'w-8 h-8 text-xs rounded-lg font-medium transition-colors',
                isFuture ? 'text-[var(--text-tertiary)] cursor-not-allowed' : 'hover:bg-[var(--surface-tertiary)]',
                isSelected
                  ? 'bg-[var(--accent-primary)] text-[var(--text-inverse)]'
                  : isToday
                  ? 'ring-1 ring-[var(--accent-primary)] text-[var(--text-primary)]'
                  : 'text-[var(--text-primary)]',
              ].join(' ')}
            >
              {day}
            </button>
          )
        })}
      </div>

      {/* today shortcut */}
      <div className="mt-3 pt-3 border-t border-[var(--border-subtle)]">
        <button
          type="button"
          onClick={() => {
            const t = toLocalDateStr(today.getFullYear(), today.getMonth(), today.getDate())
            onChange(t)
            setViewYear(today.getFullYear())
            setViewMonth(today.getMonth())
          }}
          className="text-xs text-[var(--accent-primary)] hover:underline focus-ring rounded"
        >
          Jump to today
        </button>
      </div>
    </div>
  )
}
