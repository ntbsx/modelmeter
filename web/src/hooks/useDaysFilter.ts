import { useMemo } from 'react'
import { useSearchParams } from 'react-router-dom'

const LOCAL_STORAGE_KEY = 'modelmeter_days_filter'
const DEFAULT_DAYS = 7
const MIN_DAYS = 1
const MAX_DAYS = 365

function getStoredDays(): number {
  try {
    const stored = localStorage.getItem(LOCAL_STORAGE_KEY)
    if (stored !== null) {
      const parsed = parseInt(stored, 10)
      if (!isNaN(parsed) && parsed >= MIN_DAYS && parsed <= MAX_DAYS) {
        return parsed
      }
    }
  } catch {
    // localStorage not available
  }
  return DEFAULT_DAYS
}

function setStoredDays(days: number): void {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, String(days))
  } catch {
    // localStorage not available
  }
}

function normalizeDays(raw: string | null): number {
  if (raw === null) {
    return getStoredDays()
  }
  const parsed = parseInt(raw, 10)
  if (isNaN(parsed) || parsed < MIN_DAYS || parsed > MAX_DAYS) {
    return getStoredDays()
  }
  return Math.min(parsed, MAX_DAYS)
}

export function useDaysFilter() {
  const [searchParams, setSearchParams] = useSearchParams()

  const days = useMemo(
    () => normalizeDays(searchParams.get('days')),
    [searchParams]
  )

  const setDays = (nextDays: number) => {
    const validatedDays = Math.max(MIN_DAYS, Math.min(nextDays, MAX_DAYS))
    const params = new URLSearchParams(searchParams)
    params.set('days', String(validatedDays))
    setSearchParams(params, { replace: true })
    setStoredDays(validatedDays)
  }

  return { days, setDays }
}
