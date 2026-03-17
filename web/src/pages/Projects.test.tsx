import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import Projects from './Projects'

describe('Projects page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders project usage rows with source badges from the API', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        projects: [
          {
            project_id: 'proj-1',
            project_name: 'My Project',
            project_path: '/home/user/my-project',
            usage: {
              input_tokens: 1000,
              output_tokens: 500,
              total_tokens: 1500,
              cache_read_tokens: 0,
              cache_write_tokens: 0,
            },
            total_sessions: 10,
            total_interactions: 25,
            cost_usd: 0.05,
            has_pricing: true,
            sources: ['local'],
          },
          {
            project_id: 'proj-2',
            project_name: 'Shared Project',
            project_path: '/home/user/shared',
            usage: {
              input_tokens: 2000,
              output_tokens: 1000,
              total_tokens: 3000,
              cache_read_tokens: 0,
              cache_write_tokens: 0,
            },
            total_sessions: 20,
            total_interactions: 50,
            cost_usd: 0.1,
            has_pricing: true,
            sources: ['local', 'remote-prod'],
          },
        ],
        projects_offset: 0,
        projects_returned: 2,
        total_projects: 2,
        total_sessions: 30,
        totals: {
          input_tokens: 3000,
          output_tokens: 1500,
          total_tokens: 4500,
          cache_read_tokens: 0,
          cache_write_tokens: 0,
        },
        source_scope: 'all',
        sources_considered: ['local', 'remote-prod'],
        sources_succeeded: ['local', 'remote-prod'],
        sources_failed: [],
      }),
    } as Response)

    render(<Projects />)

    expect(await screen.findByText('My Project')).toBeInTheDocument()
    expect(screen.getByText('Shared Project')).toBeInTheDocument()
    
    expect(screen.getAllByText('local')).toHaveLength(2)
    expect(screen.getAllByText('remote-prod')).toHaveLength(1)
    
    expect(fetchMock).toHaveBeenCalledWith(
      expect.stringContaining('/api/projects?days=7'),
      expect.objectContaining({ headers: {} })
    )
  })

  it('renders local source badge when sources field is missing', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        projects: [
          {
            project_id: 'proj-1',
            project_name: 'Legacy Project',
            usage: {
              input_tokens: 100,
              output_tokens: 50,
              total_tokens: 150,
              cache_read_tokens: 0,
              cache_write_tokens: 0,
            },
            total_sessions: 5,
            total_interactions: 10,
            sources: undefined,
          },
        ],
        projects_offset: 0,
        projects_returned: 1,
        total_projects: 1,
        totals: {
          input_tokens: 100,
          output_tokens: 50,
          total_tokens: 150,
          cache_read_tokens: 0,
          cache_write_tokens: 0,
        },
      }),
    } as Response)

    render(<Projects />)

    expect(await screen.findByText('Legacy Project')).toBeInTheDocument()
    expect(screen.getByText('local')).toBeInTheDocument()
  })

  it('renders an empty state when no project usage is returned', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        projects: [],
        projects_offset: 0,
        projects_returned: 0,
        total_projects: 0,
        totals: {
          input_tokens: 0,
          output_tokens: 0,
          total_tokens: 0,
          cache_read_tokens: 0,
          cache_write_tokens: 0,
        },
      }),
    } as Response)

    render(<Projects />)

    expect(await screen.findByText('No project usage found in this period.')).toBeInTheDocument()
  })
})
