import { beforeEach, describe, expect, it, vi } from 'vitest'
import { fireEvent, render, screen, waitFor } from '../test/test-utils'
import Sources from './Sources'

describe('Sources page', () => {
  beforeEach(() => {
    vi.restoreAllMocks()
  })

  it('renders configured sources from API', async () => {
    vi.spyOn(globalThis, 'fetch').mockResolvedValue({
      ok: true,
      status: 200,
      json: async () => ({
        version: 1,
        sources: [
          {
            source_id: 'remote-prod',
            kind: 'http',
            label: 'Production',
            base_url: 'https://example.com',
            db_path: null,
            has_auth: true,
            enabled: true,
          },
        ],
      }),
    } as Response)

    render(<Sources />)

    expect(await screen.findByText('remote-prod')).toBeInTheDocument()
    expect(screen.getByText('https://example.com')).toBeInTheDocument()
    expect(screen.getByText('Configured')).toBeInTheDocument()
  })

  it('runs source health checks and displays status', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.includes('/api/sources/check')) {
        return {
          ok: true,
          status: 200,
          json: async () => [
            {
              source_id: 'remote-prod',
              kind: 'http',
              is_reachable: true,
              detail: 'HTTP 200',
              error: null,
            },
          ],
        } as Response
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({
          version: 1,
          sources: [
            {
              source_id: 'remote-prod',
              kind: 'http',
              label: 'Production',
              base_url: 'https://example.com',
              db_path: null,
              has_auth: true,
              enabled: true,
            },
          ],
        }),
      } as Response
    })

    render(<Sources />)

    expect(await screen.findByText('remote-prod')).toBeInTheDocument()
    fireEvent.click(screen.getByRole('button', { name: 'Run Health Check' }))

    expect(await screen.findByText('Healthy')).toBeInTheDocument()
  })

  it('submits sqlite source form with PUT request', async () => {
    const fetchMock = vi.spyOn(globalThis, 'fetch').mockImplementation(async (input, init) => {
      const url = String(input)
      if (url.includes('/api/sources/') && init?.method === 'PUT') {
        return {
          ok: true,
          status: 200,
          json: async () => ({ version: 1, sources: [] }),
        } as Response
      }

      return {
        ok: true,
        status: 200,
        json: async () => ({ version: 1, sources: [] }),
      } as Response
    })

    render(<Sources />)

    expect(await screen.findByText('No sources configured yet.')).toBeInTheDocument()

    fireEvent.change(screen.getByPlaceholderText('local-macbook'), {
      target: { value: 'local-db' },
    })
    fireEvent.change(screen.getByPlaceholderText('/Users/me/.local/share/opencode/opencode.db'), {
      target: { value: '/tmp/opencode.db' },
    })
    fireEvent.click(screen.getByRole('button', { name: 'Add Source' }))

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/sources/local-db'),
        expect.objectContaining({ method: 'PUT' })
      )
    })
  })
})
