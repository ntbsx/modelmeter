import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import Models from './Models'

vi.mock('react-router-dom', async () => {
  const actual = await vi.importActual('react-router-dom')
  return {
    ...actual,
    useParams: vi.fn(),
  }
})

import { useParams } from 'react-router-dom'

describe('Models page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('requests all models when no provider is specified', async () => {
    vi.mocked(useParams).mockReturnValue({})
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        models: [],
        models_offset: 0,
        models_returned: 0,
        total_models: 0,
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

    render(<Models />)

    expect(await screen.findByText('No model usage found in this period.')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/models?days=7'),
      expect.objectContaining({ headers: {} })
    )
  })

  it('requests filtered models when providerId is in route params', async () => {
    vi.mocked(useParams).mockReturnValue({ providerId: 'openai' })
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        models: [
          {
            model_id: 'openai/gpt-4',
            total_sessions: 1,
            total_interactions: 1,
            usage: {
              input_tokens: 10,
              output_tokens: 20,
              total_tokens: 30,
              cache_read_tokens: 0,
              cache_write_tokens: 0,
            },
            cost_usd: null,
            has_pricing: false,
          },
        ],
        models_offset: 0,
        models_returned: 1,
        total_models: 1,
        total_sessions: 1,
        totals: {
          input_tokens: 10,
          output_tokens: 20,
          total_tokens: 30,
          cache_read_tokens: 0,
          cache_write_tokens: 0,
        },
      }),
    } as Response)

    render(<Models />)

    expect(await screen.findByText('openai/gpt-4')).toBeInTheDocument()
    expect(await screen.findByText('openai Models')).toBeInTheDocument()
    
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('provider=openai'),
      expect.objectContaining({ headers: {} })
    )
  })
})
