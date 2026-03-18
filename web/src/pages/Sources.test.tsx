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
    expect(screen.getByText('✓ Configured')).toBeInTheDocument()
  })

  it('runs source health checks and displays status', async () => {
    vi.spyOn(globalThis, 'fetch').mockImplementation(async (input) => {
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

    expect(await screen.findByText('✓ Healthy')).toBeInTheDocument()
  })

  it('submits http source form with PUT request', async () => {
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

    const headerAddBtn = screen.getByRole('button', { name: 'Add Source' })
    fireEvent.click(headerAddBtn)

    const sourceIdInput = screen.getByPlaceholderText('local-macbook')
    fireEvent.change(sourceIdInput, { target: { value: 'remote-server' } })

    const baseUrlInput = screen.getByPlaceholderText('https://modelmeter.example.com')
    fireEvent.change(baseUrlInput, { target: { value: 'https://example.com' } })

    const submitBtn = document.querySelector('button[type="submit"]') as HTMLButtonElement
    fireEvent.click(submitBtn)

    await waitFor(() => {
      expect(fetchMock).toHaveBeenCalledWith(
        expect.stringContaining('/api/sources/remote-server'),
        expect.objectContaining({ method: 'PUT' })
      )
    })
  })
})
