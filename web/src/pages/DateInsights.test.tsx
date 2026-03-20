import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import DateInsights from './DateInsights'

describe('DateInsights page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders date breakdown sections from API payload', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        day: '2026-03-20',
        timezone_offset_minutes: 0,
        usage: {
          input_tokens: 10,
          output_tokens: 5,
          cache_read_tokens: 2,
          cache_write_tokens: 1,
          total_tokens: 18,
        },
        total_sessions: 1,
        total_interactions: 1,
        cost_usd: 0.01,
        models: [
          {
            model_id: 'openai/gpt-5',
            provider: 'openai',
            usage: {
              input_tokens: 10,
              output_tokens: 5,
              cache_read_tokens: 2,
              cache_write_tokens: 1,
              total_tokens: 18,
            },
            total_sessions: 1,
            total_interactions: 1,
            cost_usd: 0.01,
            has_pricing: true,
          },
        ],
        providers: [
          {
            provider: 'openai',
            usage: {
              input_tokens: 10,
              output_tokens: 5,
              cache_read_tokens: 2,
              cache_write_tokens: 1,
              total_tokens: 18,
            },
            total_models: 1,
            total_interactions: 1,
            cost_usd: 0.01,
            has_pricing: true,
          },
        ],
        projects: [
          {
            project_id: 'p1',
            project_name: 'My Project',
            project_path: '/tmp/my-project',
            usage: {
              input_tokens: 10,
              output_tokens: 5,
              cache_read_tokens: 2,
              cache_write_tokens: 1,
              total_tokens: 18,
            },
            total_sessions: 1,
            total_interactions: 1,
            cost_usd: 0.01,
            has_pricing: true,
            sources: ['local'],
          },
        ],
        source_scope: 'local',
        sources_considered: ['local'],
        sources_succeeded: ['local'],
        sources_failed: [],
      }),
    } as Response)

    render(<DateInsights />)

    expect(await screen.findByText('openai/gpt-5')).toBeInTheDocument()
    expect(screen.getByText('openai')).toBeInTheDocument()
    expect(screen.getByText('My Project')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/date-insights?day='),
      expect.objectContaining({ headers: {} })
    )
  })
})
