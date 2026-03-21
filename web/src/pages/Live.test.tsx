import { beforeEach, describe, expect, it, vi, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import userEvent from '@testing-library/user-event'
import Live from '../Live'
import * as React from 'react'

vi.mock('../hooks/useLivePanels', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../hooks/useLivePanels')>()
  return {
    ...mod,
    useLivePanels: vi.fn(() => ({
      panels: [],
      addPanel: vi.fn(() => ({ success: true, reason: '' })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })),
  }
})

vi.mock('../hooks/useSourceScope', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../hooks/useSourceScope')>()
  return {
    ...mod,
    useSourceScope: vi.fn(() => ({ sourceScope: 'self' })),
  }
})

vi.mock('../components/LivePanel', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../components/LivePanel')>()
  return {
    default: vi.fn(({ panel, ...props }) => (
      <div data-testid={`live-panel-${panel.id}`}>
        <div>Panel: {panel.sessionTitle || panel.sessionId}</div>
      </div>
    )),
  }
})

vi.mock('../components/SessionPicker', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../components/SessionPicker')>()
  return {
    default: vi.fn(({ isOpen, onSelectSession }) => (
      <div data-testid="session-picker" style={{ display: isOpen ? 'block' : 'none' }}>
        <button onClick={() => onSelectSession({
          session_id: 'test-session-1',
          title: 'Test Session',
          project_name: null,
          directory: null,
          time_created: Date.now(),
          time_updated: Date.now(),
          time_archived: null,
          message_count: 5,
          model_count: 2,
          token_count: 1000,
          cost_usd: 0.05,
          is_active: true,
        })}>
          Select Test Session
        </button>
      </div>
    )),
  }
})

vi.mock('../components/DataTable', async (importOriginal) => {
  const mod = await importOriginal<typeof import('../components/DataTable')>()
  return {
    ...mod,
    PageHeader: ({ title, description, actions, children }) => (
      <div data-testid="page-header">
        <h1>{title}</h1>
        <p>{description}</p>
        {children}
      </div>
    ),
  }
})

const createQueryClient = () => new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
    refetchOnWindowFocus: false,
    },
  },
})

function renderWithQueryClient(ui: React.ReactElement) {
  return render(
    <QueryClientProvider client={createQueryClient()}>
      {ui}
    </QueryClientProvider>
  )
}

describe('Live page', () => {
  let queryClient: QueryClient

  beforeEach(() => {
    queryClient = createQueryClient()
    vi.clearAllMocks()
  })

  afterEach(() => {
    queryClient.clear()
  })

  it('renders page header with title and description', async () => {
    renderWithQueryClient(<Live />)

    expect(screen.getByText('Live Monitoring')).toBeInTheDocument()
    expect(screen.getByText('Monitor multiple sessions in real-time')).toBeInTheDocument()
  })

  it('renders data source notice', async () => {
    renderWithQueryClient(<Live />)

    expect(screen.getByText('Data source: This Server (self)')).toBeInTheDocument()
    expect(screen.getByText('Multi-server monitoring coming soon')).toBeInTheDocument()
  })

  it('shows empty state when no panels configured', async () => {
    const { useLivePanels } = await import('../hooks/useLivePanels')
    vi.mocked(useLivePanels).useLivePanels.mockReturnValue({
      panels: [],
      addPanel: vi.fn(),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })

    renderWithQueryClient(<Live />)

    expect(screen.getByText('No live panels configured')).toBeInTheDocument()
    expect(screen.getByText('Click "Add Panel" to start monitoring sessions')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /add panel/i })).toBeInTheDocument()
  })

  it('disables add panel button when max panels reached', async () => {
    const { useLivePanels } = await import('../hooks/useLivePanels')
    vi.mocked(useLivePanels).useLivePanels.mockReturnValue({
      panels: Array.from({ length: 6 }, (_, i) => ({
        id: `panel-${i}`,
        sessionId: `session-${i}`,
        sessionTitle: `Session ${i + 1}`,
        projectName: null,
        projectPath: null,
        position: i,
        addedAt: Date.now(),
      })),
      addPanel: vi.fn(() => ({ success: false, reason: 'max-panels' })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: true,
      panelCount: 6,
    })

    renderWithQueryClient(<Live />)

    const addButton = screen.getByRole('button', { name: /add panel/i })
    expect(addButton).toBeDisabled()
    expect(screen.getByText('Maximum 6 panels reached')).toBeInTheDocument()
  })

  it('renders live panels when configured', async () => {
    const { useLivePanels } = await import('../hooks/useLivePanels')
    const mockPanels = [
      {
        id: 'panel-1',
        sessionId: 'session-1',
        sessionTitle: 'Active Session',
        projectName: 'test-project',
        projectPath: '/path/to/project',
        position: 0,
        addedAt: Date.now(),
      },
      {
        id: 'panel-2',
        sessionId: 'session-2',
        sessionTitle: 'Inactive Session',
        projectName: null,
        projectPath: null,
        position: 1,
        addedAt: Date.now(),
      },
    ]

    vi.mocked(useLivePanels).useLivePanels.mockReturnValue({
      panels: mockPanels,
      addPanel: vi.fn(() => ({ success: true })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 2,
    })

    renderWithQueryClient(<Live />)

    expect(screen.getByTestId('live-panel-panel-1')).toBeInTheDocument()
    expect(screen.getByTestId('live-panel-panel-2')).toBeInTheDocument()
    expect(screen.getByText('Active Session')).toBeInTheDocument()
    expect(screen.getByText('Inactive Session')).toBeInTheDocument()
    expect(screen.getByText('test-project')).toBeInTheDocument()
  })

  it('opens session picker dialog when add panel button clicked', async () => {
    const user = userEvent.setup()
    const { useLivePanels } = await import('../hooks/useLivePanels')
    vi.mocked(useLivePanels).useLivePanels.mockReturnValue({
      panels: [],
      addPanel: vi.fn(() => ({ success: true })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })

    renderWithQueryClient(<Live />)

    const addButton = screen.getByRole('button', { name: /add panel/i })
    await user.click(addButton)

    expect(screen.getByTestId('session-picker')).toBeInTheDocument()
    expect(screen.getByText('Add Live Session Panel')).toBeInTheDocument()
  })

  it('closes session picker dialog when session selected', async () => {
    const user = userEvent.setup()
    const { useLivePanels } = await import('../hooks/useLivePanels')
    const mockAddPanel = vi.fn(() => ({ success: true }))
    vi.mocked(useLivePanels).useLivePanels.mockReturnValue({
      panels: [],
      addPanel: mockAddPanel,
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })

    renderWithQueryClient(<Live />)

    const addButton = screen.getByRole('button', { name: /add panel/i })
    await user.click(addButton)

    const selectButton = screen.getByText('Select Test Session')
    await user.click(selectButton)

    expect(mockAddPanel).toHaveBeenCalledWith(
      expect.objectContaining({
        session_id: 'test-session-1',
        title: 'Test Session',
      })
    )
    expect(screen.queryByTestId('session-picker')).not.toBeInTheDocument()
  })

  it('toggles global pause/resume state', async () => {
    const user = userEvent.setup()
    const { useLivePanels } = await import('../hooks/useLivePanels')
    vi.mocked(useLivePanels).useLivePanels.mockReturnValue({
      panels: [],
      addPanel: vi.fn(),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })

    renderWithQueryClient(<Live />)

    const pauseButton = screen.getByRole('button', { name: /pause all/i })
    expect(screen.getByText('Pause All')).toBeInTheDocument()

    await user.click(pauseButton)
    expect(screen.getByText('Resume All')).toBeInTheDocument()
    await user.click(pauseButton)
    expect(screen.getByText('Pause All')).toBeInTheDocument()
  })

  it('shows proper grid columns for different panel counts', async () => {
    const { useLivePanels } = await import('../hooks/useLivePanels')

    const panels1 = [{
      id: 'panel-1',
      sessionId: 'session-1',
      sessionTitle: 'Session 1',
      projectName: null,
      projectPath: null,
      position: 0,
      addedAt: Date.now(),
    }]

    const panels4 = [
      ...panels1,
      { id: 'panel-2', sessionId: 'session-2', sessionTitle: 'Session 2', projectName: null, projectPath: null, position: 1, addedAt: Date.now() },
      { id: 'panel-3', sessionId: 'session-3', sessionTitle: 'Session 3', projectName: null, projectPath: null, position: 2, addedAt: Date.now() },
      { id: 'panel-4', sessionId: 'session-4', sessionTitle: 'Session 4', projectName: null, projectPath: null, position: 3, addedAt: Date.now() },
    ]

    vi.mocked(useLivePanels).useLivePanels.mockReturnValueOnce({
      panels: panels1,
      addPanel: vi.fn(),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 1,
    }).mockReturnValueOnce({
      panels: panels4,
      addPanel: vi.fn(),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 4,
    })

    const { rerender } = renderWithQueryClient(<Live />)
    let gridElement = screen.getByRole('grid') // Assuming panels are in a grid
    expect(gridElement).toHaveClass('grid-cols-1')

    rerender(<Live />)
    gridElement = screen.getByRole('grid')
    expect(gridElement).toHaveClass('lg:grid-cols-2', 'xl:grid-cols-3')
  })
})
