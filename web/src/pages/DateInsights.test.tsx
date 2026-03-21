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
        sessions: [
          {
            session_id: 's1-abc-def',
            project_id: 'p1',
            project_name: 'My Project',
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
                total_interactions: 1,
                cost_usd: 0.01,
                has_pricing: true,
              },
            ],
            total_tokens: 18,
            total_interactions: 1,
            cost_usd: 0.01,
            has_pricing: true,
            started_at: '2026-03-20T10:30:00+00:00',
          },
        ],
        sources_failed: [],
      }),
    } as Response)

    render(<DateInsights />)

    expect(await screen.findByText('gpt-5')).toBeInTheDocument()
    expect(screen.getAllByText('openai').length).toBeGreaterThanOrEqual(1)

    // Switch to Projects tab
    const projectsTab = screen.getByRole('button', { name: /projects/i })
    await projectsTab.click()
    expect(await screen.findByText('My Project')).toBeInTheDocument()
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/date-insights?day='),
      expect.objectContaining({ headers: {} })
    )
  })

  it('shows session cards when Sessions tab is clicked', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        day: '2026-03-20',
        timezone_offset_minutes: 0,
        usage: { input_tokens: 10, output_tokens: 5, cache_read_tokens: 0, cache_write_tokens: 0, total_tokens: 15 },
        total_sessions: 1,
        total_interactions: 1,
        cost_usd: 0.01,
        models: [],
        providers: [],
        projects: [],
        sessions: [
          {
            session_id: 's1-abc-def-ghi',
            project_id: 'p1',
            project_name: 'Test Project',
            models: [
              {
                model_id: 'anthropic/claude-sonnet-4-5',
                provider: 'anthropic',
                usage: { input_tokens: 10, output_tokens: 5, cache_read_tokens: 0, cache_write_tokens: 0, total_tokens: 15 },
                total_interactions: 1,
                cost_usd: 0.01,
                has_pricing: true,
              },
            ],
            total_tokens: 15,
            total_interactions: 1,
            cost_usd: 0.01,
            has_pricing: true,
            started_at: '2026-03-20T14:00:00+00:00',
          },
        ],
        source_scope: 'local',
        sources_considered: ['local'],
        sources_succeeded: ['local'],
        sources_failed: [],
      }),
    } as Response)

    render(<DateInsights />)

    // Wait for data to load, then click Sessions tab
    const sessionsTab = await screen.findByRole('button', { name: /sessions/i })
    await sessionsTab.click()

    // Session card content
    expect(await screen.findByText('Test Project')).toBeInTheDocument()
    expect(screen.getByText('claude-sonnet-4-5')).toBeInTheDocument()
    expect(screen.getAllByText('anthropic').length).toBeGreaterThanOrEqual(1)
  })
})
