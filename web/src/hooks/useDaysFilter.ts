import { useMemo } from 'react'
import { useLocation, useSearchParams } from 'react-router-dom'

const LOCAL_STORAGE_KEY_PREFIX = 'modelmeter_days_filter'
const DEFAULT_DAYS = 7
const MIN_DAYS = 1
const MAX_DAYS = 365

function getStorageKey(scope: string): string {
  return `${LOCAL_STORAGE_KEY_PREFIX}:${scope}`
}

function getStoredDays(scope: string): number {
  try {
    const stored = localStorage.getItem(getStorageKey(scope))
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

function setStoredDays(scope: string, days: number): void {
  try {
    localStorage.setItem(getStorageKey(scope), String(days))
  } catch {
    // localStorage not available
  }
}

function normalizeDays(raw: string | null, scope: string): number {
  if (raw === null) {
    return getStoredDays(scope)
  }
  const parsed = parseInt(raw, 10)
  if (isNaN(parsed) || parsed < MIN_DAYS || parsed > MAX_DAYS) {
    return getStoredDays(scope)
  }
  return Math.min(parsed, MAX_DAYS)
}

function normalizeScopeFromPath(pathname: string): string {
  if (pathname === '/') {
    return 'overview'
  }
  if (pathname === '/models') {
    return 'models'
  }
  if (pathname.startsWith('/models/provider/')) {
    return 'models'
  }
  if (pathname.startsWith('/models/')) {
    return 'model-detail'
  }
  if (pathname === '/projects') {
    return 'projects'
  }
  if (pathname.startsWith('/projects/')) {
    return 'project-detail'
  }
  return pathname.replaceAll('/', '_') || 'default'
}

export function useDaysFilter(scopeOverride?: string) {
  const [searchParams, setSearchParams] = useSearchParams()
  const location = useLocation()
  const scope = scopeOverride ?? normalizeScopeFromPath(location.pathname)

  const days = useMemo(
    () => normalizeDays(searchParams.get('days'), scope),
    [scope, searchParams]
  )

  const setDays = (nextDays: number) => {
    const validatedDays = Math.max(MIN_DAYS, Math.min(nextDays, MAX_DAYS))
    const params = new URLSearchParams(searchParams)
    params.set('days', String(validatedDays))
    setSearchParams(params, { replace: true })
    setStoredDays(scope, validatedDays)
  }

  return { days, setDays }
}
