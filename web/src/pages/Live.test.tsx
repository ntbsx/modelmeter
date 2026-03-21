import { beforeEach, describe, expect, it, vi } from 'vitest'
import { render, screen } from '../test/test-utils'
import userEvent from '@testing-library/user-event'
import type { ReactNode } from 'react'

import Live from './Live'
import { useLivePanels, type LivePanel } from '../hooks/useLivePanels'

vi.mock('../hooks/useLivePanels', () => ({
  useLivePanels: vi.fn(),
}))

vi.mock('../hooks/useSourceScope', () => ({
  useSourceScope: () => ({ sourceScope: 'self' }),
}))

vi.mock('../components/LivePanel', () => ({
  default: ({ panel }: { panel: LivePanel }) => <div data-testid={`panel-${panel.id}`} />,
}))

type SessionPickerProps = {
  isOpen: boolean
  onClose: () => void
  onSelectSession: (session: {
    session_id: string
    title: string | null
    project_name: string | null
    directory: string | null
    time_created: number
    time_updated: number
    time_archived: number | null
    message_count: number
    model_count: number
    token_count: number
    cost_usd: number | null
    is_active: boolean
  }) => void
}

vi.mock('../components/SessionPicker', () => ({
  default: ({ isOpen, onClose, onSelectSession }: SessionPickerProps) =>
    isOpen ? (
      <div data-testid="session-picker">
        <button
          type="button"
          onClick={() => {
            onSelectSession({
              session_id: 's1',
              title: 'Session 1',
              project_name: null,
              directory: null,
              time_created: 0,
              time_updated: 0,
              time_archived: null,
              message_count: 0,
              model_count: 0,
              token_count: 0,
              cost_usd: null,
              is_active: true,
            })
            onClose()
          }}
        >
          Select
        </button>
      </div>
    ) : null,
}))

type PageHeaderProps = {
  title: string
  description: string
  actions?: ReactNode
}

vi.mock('../components/DataTable', () => ({
  PageHeader: ({ title, description, actions }: PageHeaderProps) => (
    <header>
      <h1>{title}</h1>
      <p>{description}</p>
      {actions}
    </header>
  ),
}))

const mockedUseLivePanels = vi.mocked(useLivePanels)

function makePanels(count: number): LivePanel[] {
  return Array.from({ length: count }, (_, i) => ({
    id: `p${i}`,
    sessionId: `s${i}`,
    sessionTitle: `Session ${i}`,
    projectName: null,
    projectPath: null,
    position: i,
    addedAt: 0,
  }))
}

describe('Live page', () => {
  beforeEach(() => {
    mockedUseLivePanels.mockReturnValue({
      panels: [],
      addPanel: vi.fn(() => ({ success: true })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })
  })

  it('renders title and 6-hour notice', () => {
    render(<Live />)
    expect(screen.getByText('Live Monitoring')).toBeInTheDocument()
    expect(screen.getByText('Metrics show activity from the last 6 hours')).toBeInTheDocument()
  })

  it('shows empty state when no panels exist', () => {
    render(<Live />)
    expect(screen.getByText('No live panels configured')).toBeInTheDocument()
  })

  it('renders panels when available', () => {
    mockedUseLivePanels.mockReturnValue({
      panels: makePanels(2),
      addPanel: vi.fn(() => ({ success: true })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 2,
    })

    render(<Live />)
    expect(screen.getByTestId('panel-p0')).toBeInTheDocument()
    expect(screen.getByTestId('panel-p1')).toBeInTheDocument()
  })

  it('disables add button when max reached and shows inline message', () => {
    mockedUseLivePanels.mockReturnValue({
      panels: makePanels(6),
      addPanel: vi.fn(() => ({ success: false, reason: 'max-panels' })),
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: true,
      panelCount: 6,
    })

    render(<Live />)
    const addButton = screen.getByRole('button', { name: /add panel/i })
    expect(addButton).toBeDisabled()
    expect(screen.getByText('Panel limit reached: maximum 6 live panels.')).toBeInTheDocument()
  })

  it('opens picker and adds session', async () => {
    const user = userEvent.setup()
    const addPanel = vi.fn(() => ({ success: true }))
    mockedUseLivePanels.mockReturnValue({
      panels: [],
      addPanel,
      removePanel: vi.fn(),
      maxPanels: 6,
      reachedMax: false,
      panelCount: 0,
    })

    render(<Live />)
    await user.click(screen.getByRole('button', { name: /add panel/i }))
    expect(screen.getByTestId('session-picker')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Select' }))
    expect(addPanel).toHaveBeenCalledTimes(1)
  })
})
