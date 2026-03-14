import { describe, it, expect } from 'vitest'
import { formatTokens, formatUsd, cn } from './utils'

describe('formatTokens', () => {
  it('formats small numbers using locale string', () => {
    expect(formatTokens(0)).toBe('0')
    expect(formatTokens(999)).toBe('999')
  })

  it('formats thousands with K suffix', () => {
    expect(formatTokens(1000)).toBe('1.0K')
    expect(formatTokens(1500)).toBe('1.5K')
    expect(formatTokens(999000)).toBe('999.0K')
  })

  it('formats millions with M suffix', () => {
    expect(formatTokens(1000000)).toBe('1.0M')
    expect(formatTokens(2500000)).toBe('2.5M')
  })

  it('formats billions with B suffix', () => {
    expect(formatTokens(1000000000)).toBe('1.0B')
    expect(formatTokens(3700000000)).toBe('3.7B')
  })
})

describe('formatUsd', () => {
  it('formats zero with four decimal places', () => {
    expect(formatUsd(0)).toBe('$0.0000')
  })

  it('formats small amounts with four decimal places', () => {
    expect(formatUsd(0.01)).toBe('$0.0100')
    expect(formatUsd(0.5)).toBe('$0.5000')
  })

  it('formats amounts >= 1 with two decimal places', () => {
    expect(formatUsd(1.5)).toBe('$1.50')
    expect(formatUsd(100)).toBe('$100.00')
  })

  it('formats thousands with K suffix', () => {
    expect(formatUsd(1000)).toBe('$1.0K')
    expect(formatUsd(1500)).toBe('$1.5K')
  })

  it('formats millions with M suffix', () => {
    expect(formatUsd(1000000)).toBe('$1.0M')
  })

  it('formats billions with B suffix', () => {
    expect(formatUsd(1000000000)).toBe('$1.0B')
  })
})

describe('cn', () => {
  it('merges class names', () => {
    expect(cn('foo', 'bar')).toBe('foo bar')
  })

  it('handles conditional classes', () => {
    expect(cn('base', true && 'active')).toBe('base active')
    expect(cn('base', false && 'active')).toBe('base')
  })

  it('merges tailwind classes correctly', () => {
    expect(cn('px-2 py-1', 'px-4')).toBe('py-1 px-4')
  })
})
