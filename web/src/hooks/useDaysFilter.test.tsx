import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { useDaysFilter } from './useDaysFilter'

const LOCAL_STORAGE_KEY = 'modelmeter_days_filter:overview'

function makeWrapper(initialSearch = '') {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={[`/${initialSearch}`]}>{children}</MemoryRouter>
  }
}

describe('useDaysFilter', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('initial days value', () => {
    it('defaults to 7 when no URL param and no localStorage', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      expect(result.current.days).toBe(7)
    })

    it('reads days from URL param', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=30'),
      })
      expect(result.current.days).toBe(30)
    })

    it('reads days from localStorage when no URL param', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, '14')
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      expect(result.current.days).toBe(14)
    })

    it('URL param takes precedence over localStorage', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, '14')
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=30'),
      })
      expect(result.current.days).toBe(30)
    })
  })

  describe('normalization', () => {
    it('clamps days to MAX_DAYS (365) from URL param', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=9999'),
      })
      expect(result.current.days).toBe(7)
    })

    it('falls back to default when URL param is below MIN_DAYS', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=0'),
      })
      expect(result.current.days).toBe(7)
    })

    it('falls back to default when URL param is not a number', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=abc'),
      })
      expect(result.current.days).toBe(7)
    })

    it('falls back to default when localStorage value is above MAX_DAYS', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, '9999')
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      expect(result.current.days).toBe(7)
    })

    it('falls back to default when localStorage value is invalid', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'bad')
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      expect(result.current.days).toBe(7)
    })

    it('accepts boundary value MAX_DAYS (365) from URL param', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=365'),
      })
      expect(result.current.days).toBe(365)
    })

    it('accepts boundary value MIN_DAYS (1) from URL param', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), {
        wrapper: makeWrapper('?days=1'),
      })
      expect(result.current.days).toBe(1)
    })
  })

  describe('setDays', () => {
    it('updates URL search params when setDays is called', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      act(() => {
        result.current.setDays(30)
      })
      expect(result.current.days).toBe(30)
    })

    it('persists days to localStorage when setDays is called', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      act(() => {
        result.current.setDays(90)
      })
      expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe('90')
    })

    it('clamps value to MAX_DAYS (365) in setDays', () => {
      const { result } = renderHook(() => useDaysFilter('overview'), { wrapper: makeWrapper() })
      act(() => {
        result.current.setDays(9999)
      })
      expect(result.current.days).toBe(365)
      expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe('365')
    })

    it('clamps value to MIN_DAYS (1) in setDays', () => {
      const { result } = renderHook(() => useDaysFilter(), { wrapper: makeWrapper() })
      act(() => {
        result.current.setDays(0)
      })
      expect(result.current.days).toBe(1)
      expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe('1')
    })
  })
})
