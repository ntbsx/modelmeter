import { describe, it, expect, beforeEach } from 'vitest'
import { renderHook, act } from '@testing-library/react'
import type { ReactNode } from 'react'
import { MemoryRouter } from 'react-router-dom'
import { useSourceScope } from './useSourceScope'

const LOCAL_STORAGE_KEY = 'modelmeter_source_scope'

function makeWrapper(initialSearch = '') {
  return function Wrapper({ children }: { children: ReactNode }) {
    return <MemoryRouter initialEntries={[`/${initialSearch}`]}>{children}</MemoryRouter>
  }
}

describe('useSourceScope', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  describe('initial sourceScope value', () => {
    it('defaults to self when no URL param and no localStorage', () => {
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      expect(result.current.sourceScope).toBe('self')
    })

    it('reads source_scope=all from URL param', () => {
      const { result } = renderHook(() => useSourceScope(), {
        wrapper: makeWrapper('?source_scope=all'),
      })
      expect(result.current.sourceScope).toBe('all')
    })

    it('reads source_scope=self from URL param', () => {
      const { result } = renderHook(() => useSourceScope(), {
        wrapper: makeWrapper('?source_scope=self'),
      })
      expect(result.current.sourceScope).toBe('self')
    })

    it('reads source scope from localStorage when no URL param', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'all')
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      expect(result.current.sourceScope).toBe('all')
    })

    it('URL param takes precedence over localStorage', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'all')
      const { result } = renderHook(() => useSourceScope(), {
        wrapper: makeWrapper('?source_scope=self'),
      })
      expect(result.current.sourceScope).toBe('self')
    })

    it('handles source:custom-source format in URL', () => {
      const { result } = renderHook(() => useSourceScope(), {
        wrapper: makeWrapper('?source_scope=source:github'),
      })
      expect(result.current.sourceScope).toBe('source:github')
    })

    it('falls back to self for invalid source scope in URL', () => {
      const { result } = renderHook(() => useSourceScope(), {
        wrapper: makeWrapper('?source_scope=invalid'),
      })
      expect(result.current.sourceScope).toBe('self')
    })

    it('falls back to self when localStorage value is invalid', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'invalid')
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      expect(result.current.sourceScope).toBe('self')
    })

    it('handles source:custom-source format in localStorage', () => {
      localStorage.setItem(LOCAL_STORAGE_KEY, 'source:production')
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      expect(result.current.sourceScope).toBe('source:production')
    })
  })

  describe('setSourceScope', () => {
    it('updates URL search params when setSourceScope is called with self', () => {
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      act(() => {
        result.current.setSourceScope('self')
      })
      expect(result.current.sourceScope).toBe('self')
    })

    it('updates URL search params when setSourceScope is called with all', () => {
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      act(() => {
        result.current.setSourceScope('all')
      })
      expect(result.current.sourceScope).toBe('all')
    })

    it('updates URL search params when setSourceScope is called with source:id', () => {
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      act(() => {
        result.current.setSourceScope('source:staging')
      })
      expect(result.current.sourceScope).toBe('source:staging')
    })

    it('persists scope to localStorage when setSourceScope is called', () => {
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      act(() => {
        result.current.setSourceScope('all')
      })
      expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe('all')
    })

    it('persists source:id scope to localStorage', () => {
      const { result } = renderHook(() => useSourceScope(), { wrapper: makeWrapper() })
      act(() => {
        result.current.setSourceScope('source:backup')
      })
      expect(localStorage.getItem(LOCAL_STORAGE_KEY)).toBe('source:backup')
    })
  })
})
