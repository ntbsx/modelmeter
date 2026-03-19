import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import Providers from './Providers'

describe('Providers page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders provider usage rows from the API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        providers: [
          {
            provider: 'OpenAI',
            total_models: 3,
            total_interactions: 42,
            usage: {
              input_tokens: 100,
              output_tokens: 200,
              total_tokens: 300,
              cache_read_tokens: 0,
              cache_write_tokens: 0,
            },
            cost_usd: 12.34,
            has_pricing: true,
          },
        ],
        providers_offset: 0,
        providers_returned: 1,
        total_providers: 1,
        total_sessions: 9,
        totals: {
          input_tokens: 100,
          output_tokens: 200,
          total_tokens: 300,
          cache_read_tokens: 0,
          cache_write_tokens: 0,
        },
      }),
    } as Response)

    render(<Providers />)

    expect(await screen.findByText('OpenAI')).toBeInTheDocument()
    expect(screen.getByText('42')).toBeInTheDocument()
    expect(screen.getByText('300')).toBeInTheDocument()
    expect(screen.getByText('$12.34')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/providers?days=7'),
      expect.objectContaining({ headers: {} })
    )
  })

  it('renders an empty state when no provider usage is returned', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        providers: [],
        providers_offset: 0,
        providers_returned: 0,
        total_providers: 0,
        total_sessions: 0,
        totals: {
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
          cache_read_tokens: 0,
          cache_write_tokens: 0,
        },
      }),
    } as Response)

    render(<Providers />)

    expect(await screen.findByText('No provider usage found in this period.')).toBeInTheDocument()
    expect(screen.getByText('Make API calls to start tracking usage across your providers.')).toBeInTheDocument()
  })
})
