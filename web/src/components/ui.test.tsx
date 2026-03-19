import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '../test/test-utils'
import { Card, StatCard, Badge, Button } from './ui'

describe('Card', () => {
  it('renders children content', () => {
    render(<Card>Card content</Card>)
    expect(screen.getByText('Card content')).toBeInTheDocument()
  })

  it('applies custom className', () => {
    const { container } = render(<Card className="custom-class">Content</Card>)
    expect(container.firstChild).toHaveClass('custom-class')
  })

  it('renders with different padding variants', () => {
    const { rerender } = render(<Card padding="none">No padding</Card>)
    expect(screen.getByText('No padding')).toBeInTheDocument()

    rerender(<Card padding="sm">Small padding</Card>)
    expect(screen.getByText('Small padding')).toBeInTheDocument()

    rerender(<Card padding="md">Medium padding</Card>)
    expect(screen.getByText('Medium padding')).toBeInTheDocument()

    rerender(<Card padding="lg">Large padding</Card>)
    expect(screen.getByText('Large padding')).toBeInTheDocument()
  })

  it('applies hover style when hover is true', () => {
    const { container } = render(<Card hover>Hoverable card</Card>)
    expect(container.firstChild).toHaveClass('ds-surface-hover')
  })
})

describe('Badge', () => {
  it('renders children content', () => {
    render(<Badge>Badge text</Badge>)
    expect(screen.getByText('Badge text')).toBeInTheDocument()
  })

  it('renders with different variants', () => {
    const variants: Array<'default' | 'primary' | 'success' | 'warning' | 'error'> = [
      'default',
      'primary',
      'success',
      'warning',
      'error',
    ]

    variants.forEach(variant => {
      const { container } = render(<Badge variant={variant}>{variant}</Badge>)
      expect(container.firstChild).toHaveClass(`ds-badge-${variant}`)
    })
  })

  it('renders with dot indicator when dot is true', () => {
    render(<Badge dot>With dot</Badge>)
    const dotElement = document.querySelector('.rounded-full')
    expect(dotElement).toBeInTheDocument()
  })

  it('applies title attribute when provided', () => {
    render(<Badge title="Tooltip text">Hover me</Badge>)
    expect(screen.getByText('Hover me')).toHaveAttribute('title', 'Tooltip text')
  })
})

describe('Button', () => {
  it('renders children content', () => {
    render(<Button>Click me</Button>)
    expect(screen.getByRole('button', { name: 'Click me' })).toBeInTheDocument()
  })

  it('renders with different variants', () => {
    const variants: Array<'primary' | 'secondary' | 'ghost'> = ['primary', 'secondary', 'ghost']

    variants.forEach(variant => {
      const { getByRole } = render(
        <Button variant={variant}>{variant} button</Button>
      )
      expect(getByRole('button', { name: `${variant} button` })).toBeInTheDocument()
    })
  })

  it('renders with different sizes', () => {
    const sizes: Array<'sm' | 'md' | 'lg'> = ['sm', 'md', 'lg']

    sizes.forEach(size => {
      render(<Button size={size}>{size} size</Button>)
      expect(screen.getByRole('button', { name: `${size} size` })).toBeInTheDocument()
    })
  })

  it('handles click events', () => {
    const handleClick = vi.fn()
    render(<Button onClick={handleClick}>Click me</Button>)
    
    fireEvent.click(screen.getByRole('button', { name: 'Click me' }))
    expect(handleClick).toHaveBeenCalledTimes(1)
  })

  it('disables button when disabled is true', () => {
    const handleClick = vi.fn()
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>
    )
    
    const button = screen.getByRole('button', { name: 'Disabled' })
    expect(button).toBeDisabled()
  })

  it('does not call onClick when disabled', () => {
    const handleClick = vi.fn()
    render(
      <Button disabled onClick={handleClick}>
        Disabled
      </Button>
    )
    
    fireEvent.click(screen.getByRole('button', { name: 'Disabled' }))
    expect(handleClick).not.toHaveBeenCalled()
  })

  it('renders as different button types', () => {
    const { getByRole: getByRoleSubmit } = render(<Button type="submit">Submit</Button>)
    expect(getByRoleSubmit('button', { name: 'Submit' })).toHaveAttribute('type', 'submit')

    const { getByRole: getByRoleReset } = render(<Button type="reset">Reset</Button>)
    expect(getByRoleReset('button', { name: 'Reset' })).toHaveAttribute('type', 'reset')

    const { getByRole: getByRoleButton } = render(<Button type="button">Button</Button>)
    expect(getByRoleButton('button', { name: 'Button' })).toHaveAttribute('type', 'button')
  })
})

describe('StatCard', () => {
  it('renders label and value', () => {
    render(<StatCard label="Total Users" value="1,234" />)
    expect(screen.getByText('Total Users')).toBeInTheDocument()
    expect(screen.getByText('1,234')).toBeInTheDocument()
  })

  it('renders subtitle when provided', () => {
    render(<StatCard label="Cost" value="$50.00" subtitle="via API" />)
    expect(screen.getByText('via API')).toBeInTheDocument()
  })

  it('renders with different accent colors', () => {
    const accents: Array<'default' | 'blue' | 'green' | 'amber' | 'purple'> = [
      'default',
      'blue',
      'green',
      'amber',
      'purple',
    ]

    accents.forEach(accent => {
      const { container } = render(
        <StatCard label={accent} value="100" accent={accent} />
      )
      expect(container.firstChild).toBeInTheDocument()
    })
  })

  it('renders trend indicator when provided', () => {
    render(
      <StatCard
        label="Growth"
        value="25%"
        trend={{ value: 12.5, direction: 'up' }}
      />
    )
    expect(screen.getByText('12.5%')).toBeInTheDocument()
  })

  it('renders trend with down direction', () => {
    render(
      <StatCard
        label="Decline"
        value="10%"
        trend={{ value: 5, direction: 'down' }}
      />
    )
    expect(screen.getByText('5%')).toBeInTheDocument()
  })

  it('renders trend with neutral direction', () => {
    render(
      <StatCard
        label="Stable"
        value="100"
        trend={{ value: 0, direction: 'neutral' }}
      />
    )
    expect(screen.getByText('0%')).toBeInTheDocument()
  })

  it('applies animation delay when delay is provided', () => {
    const { container } = render(<StatCard label="Delayed" value="10" delay={150} />)
    expect(container.firstChild).toHaveStyle({ animationDelay: '150ms' })
  })

  it('renders icon when provided', () => {
    render(
      <StatCard
        label="With Icon"
        value="42"
        icon={<span data-testid="custom-icon">Icon</span>}
      />
    )
    expect(screen.getAllByTestId('custom-icon').length).toBeGreaterThan(0)
  })
})
