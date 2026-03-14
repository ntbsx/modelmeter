import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../test/test-utils'
import TimeRangeFilter from './TimeRangeFilter'

describe('TimeRangeFilter', () => {
  it('renders all time range options', () => {
    const onChange = vi.fn()
    render(<TimeRangeFilter days={7} onChange={onChange} />)

    // Check desktop buttons exist
    expect(screen.getByRole('button', { name: '24h' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '7d' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '30d' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '90d' })).toBeInTheDocument()
  })

  it('highlights the active time range', () => {
    const onChange = vi.fn()
    render(<TimeRangeFilter days={30} onChange={onChange} />)

    const activeButton = screen.getByRole('button', { name: '30d' })
    expect(activeButton).toHaveClass('bg-blue-600')
  })

  it('calls onChange when a different range is selected', () => {
    const onChange = vi.fn()
    render(<TimeRangeFilter days={7} onChange={onChange} />)

    const thirtyDayButton = screen.getByRole('button', { name: '30d' })
    fireEvent.click(thirtyDayButton)

    expect(onChange).toHaveBeenCalledWith(30)
  })

  it('has a mobile select with all options', () => {
    const onChange = vi.fn()
    render(<TimeRangeFilter days={7} onChange={onChange} />)

    const select = screen.getByRole('combobox', { name: 'Select time range' })
    expect(select).toBeInTheDocument()
    expect(select).toHaveValue('7')
  })

  it('calls onChange when mobile select changes', () => {
    const onChange = vi.fn()
    render(<TimeRangeFilter days={7} onChange={onChange} />)

    const select = screen.getByRole('combobox', { name: 'Select time range' })
    fireEvent.change(select, { target: { value: '90' } })

    expect(onChange).toHaveBeenCalledWith(90)
  })
})
