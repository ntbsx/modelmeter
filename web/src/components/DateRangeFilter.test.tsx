import { describe, it, expect, vi } from 'vitest'
import { render, screen, fireEvent } from '../test/test-utils'
import DateRangeFilter from './DateRangeFilter'

describe('DateRangeFilter', () => {
  it('renders all preset time range options', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    // Check desktop buttons exist
    expect(screen.getByRole('button', { name: '24h' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '7d' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '30d' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '90d' })).toBeInTheDocument()
  })

  it('renders the Custom button', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    expect(screen.getByRole('button', { name: /custom/i })).toBeInTheDocument()
  })

  it('highlights the active preset', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={30} onChange={onChange} />)

    const activeButton = screen.getByRole('button', { name: '30d' })
    expect(activeButton).toHaveClass('bg-blue-600')
  })

  it('shows custom value when days is not a preset', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={14} onChange={onChange} />)

    // Custom button should show "14d" and be highlighted
    const customButton = screen.getByRole('button', { name: /14d/i })
    expect(customButton).toHaveClass('bg-blue-600')
  })

  it('calls onChange when a preset is selected', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    const thirtyDayButton = screen.getByRole('button', { name: '30d' })
    fireEvent.click(thirtyDayButton)

    expect(onChange).toHaveBeenCalledWith(30)
  })

  it('opens the custom days picker when Custom is clicked', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    const customButton = screen.getByRole('button', { name: /custom/i })
    fireEvent.click(customButton)

    // Check that the number input appears
    expect(screen.getByLabelText(/number of days/i)).toBeInTheDocument()
  })

  it('applies custom days when Apply is clicked', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    // Open the picker
    const customButton = screen.getByRole('button', { name: /custom/i })
    fireEvent.click(customButton)

    // Enter a custom value
    const input = screen.getByLabelText(/number of days/i)
    fireEvent.change(input, { target: { value: '14' } })

    // Click apply
    const applyButton = screen.getByRole('button', { name: /apply/i })
    fireEvent.click(applyButton)

    expect(onChange).toHaveBeenCalledWith(14)
  })

  it('applies custom days on Enter key', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    // Open the picker
    const customButton = screen.getByRole('button', { name: /custom/i })
    fireEvent.click(customButton)

    // Enter a custom value and press Enter
    const input = screen.getByLabelText(/number of days/i)
    fireEvent.change(input, { target: { value: '21' } })
    fireEvent.keyDown(input, { key: 'Enter' })

    expect(onChange).toHaveBeenCalledWith(21)
  })

  it('has a mobile select with all options including custom', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    const select = screen.getByRole('combobox', { name: 'Select time range' })
    expect(select).toBeInTheDocument()
    expect(select).toHaveValue('7')

    // Check for custom option
    const options = select.querySelectorAll('option')
    const optionValues = Array.from(options).map((o) => o.value)
    expect(optionValues).toContain('custom')
  })

  it('calls onChange when mobile select changes to a preset', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    const select = screen.getByRole('combobox', { name: 'Select time range' })
    fireEvent.change(select, { target: { value: '90' } })

    expect(onChange).toHaveBeenCalledWith(90)
  })

  it('closes the picker when Cancel is clicked', () => {
    const onChange = vi.fn()
    render(<DateRangeFilter days={7} onChange={onChange} />)

    // Open the picker
    const customButton = screen.getByRole('button', { name: /custom/i })
    fireEvent.click(customButton)

    expect(screen.getByLabelText(/number of days/i)).toBeInTheDocument()

    // Click cancel
    const cancelButton = screen.getByRole('button', { name: /cancel/i })
    fireEvent.click(cancelButton)

    // Picker should be closed
    expect(screen.queryByLabelText(/number of days/i)).not.toBeInTheDocument()
    // onChange should NOT have been called
    expect(onChange).not.toHaveBeenCalled()
  })
})
