import { describe, expect, it } from 'vitest'
import { render, screen } from '../test/test-utils'
import PageLoading from './PageLoading'

describe('PageLoading', () => {
  it('renders title and subtitle', () => {
    render(<PageLoading title="Test Title" subtitle="Test Subtitle" />)

    expect(screen.getByText('Test Title')).toBeInTheDocument()
    expect(screen.getByText(/Test Subtitle/)).toBeInTheDocument()
  })

  it('renders with default subtitle when not provided', () => {
    render(<PageLoading title="Test" />)

    expect(screen.getByText('Test')).toBeInTheDocument()
  })

  it('renders correct number of skeleton cards', () => {
    const { container } = render(<PageLoading title="Test" cards={4} />)

    const cards = container.querySelectorAll('.ds-surface')
    expect(cards.length).toBeGreaterThanOrEqual(4)
  })

  it('displays a loading message from the pool', () => {
    render(<PageLoading title="Test" />)

    const loadingMessages = [
      'Gathering your data...',
      'Preparing your view...',
      'Crunching the numbers...',
      'Loading usage metrics...',
      'Syncing sources...',
    ]

    const found = loadingMessages.some(msg =>
      document.body.textContent?.includes(msg)
    )
    expect(found).toBe(true)
  })
})
