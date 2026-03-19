import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '../test/test-utils'
import { DataTable, PageHeader, SectionHeader, EmptyState, StatGrid } from './DataTable'

type TestItem = { name: string; value: number }

describe('DataTable', () => {
  const columns: Array<{ key: keyof TestItem; header: string; align?: 'right' }> = [
    { key: 'name', header: 'Name' },
    { key: 'value', header: 'Value', align: 'right' },
  ]

  const data: TestItem[] = [
    { name: 'Item 1', value: 100 },
    { name: 'Item 2', value: 200 },
  ]

  it('renders table with data', () => {
    render(
      <DataTable columns={columns} data={data} keyExtractor={item => item.name} />
    )

    expect(screen.getByText('Item 1')).toBeInTheDocument()
    expect(screen.getByText('Item 2')).toBeInTheDocument()
    expect(screen.getByText('100')).toBeInTheDocument()
    expect(screen.getByText('200')).toBeInTheDocument()
  })

  it('renders table headers', () => {
    render(
      <DataTable columns={columns} data={data} keyExtractor={item => item.name} />
    )

    expect(screen.getByText('Name')).toBeInTheDocument()
    expect(screen.getByText('Value')).toBeInTheDocument()
  })

  it('renders empty message when data is empty', () => {
    render(
      <DataTable
        columns={columns}
        data={[] as TestItem[]}
        keyExtractor={item => item.name}
        emptyMessage="No items found"
      />
    )

    expect(screen.getByText('No items found')).toBeInTheDocument()
  })

  it('renders default empty message when not provided', () => {
    render(
      <DataTable columns={columns} data={[] as TestItem[]} keyExtractor={item => item.name} />
    )

    expect(screen.getByText('No data available')).toBeInTheDocument()
  })

  it('calls onRowClick when row is clicked', () => {
    const handleRowClick = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={data}
        keyExtractor={item => item.name}
        onRowClick={handleRowClick}
      />
    )

    fireEvent.click(screen.getByText('Item 1'))
    expect(handleRowClick).toHaveBeenCalledWith(data[0])
  })

  it('calls onRowClick when Enter key is pressed', () => {
    const handleRowClick = vi.fn()
    render(
      <DataTable
        columns={columns}
        data={data}
        keyExtractor={item => item.name}
        onRowClick={handleRowClick}
      />
    )

    const row = screen.getByText('Item 2').closest('tr')
    fireEvent.keyDown(row!, { key: 'Enter' })
    expect(handleRowClick).toHaveBeenCalledWith(data[1])
  })

  it('renders custom cell content via render function', () => {
    const columnsWithRender = [
      { key: 'name', header: 'Name', render: (row: { name: string }) => <span data-testid="custom">{row.name.toUpperCase()}</span> },
      { key: 'value', header: 'Value' },
    ]

    render(
      <DataTable columns={columnsWithRender} data={data} keyExtractor={item => item.name} />
    )

    expect(screen.getAllByTestId('custom').length).toBeGreaterThan(0)
  })

  it('applies align classes correctly', () => {
    const columnsAligned = [
      { key: 'name', header: 'Name', align: 'left' as const },
      { key: 'value', header: 'Value', align: 'right' as const },
    ]

    render(
      <DataTable columns={columnsAligned} data={data} keyExtractor={item => item.name} />
    )

    const valueHeader = screen.getByText('Value')
    expect(valueHeader.closest('th')).toHaveClass('text-right')
  })
})

describe('PageHeader', () => {
  it('renders title', () => {
    render(<PageHeader title="Page Title" />)
    expect(screen.getByText('Page Title')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<PageHeader title="Title" description="Page description" />)
    expect(screen.getByText('Page description')).toBeInTheDocument()
  })

  it('does not render description when not provided', () => {
    const { container } = render(<PageHeader title="Title" />)
    expect(container.querySelector('p')).not.toBeInTheDocument()
  })

  it('renders actions when provided', () => {
    render(
      <PageHeader
        title="Title"
        actions={<button>Action</button>}
      />
    )
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
  })
})

describe('SectionHeader', () => {
  it('renders title', () => {
    render(<SectionHeader title="Section Title" />)
    expect(screen.getByText('Section Title')).toBeInTheDocument()
  })

  it('renders description when provided', () => {
    render(<SectionHeader title="Title" description="Section description" />)
    expect(screen.getByText('Section description')).toBeInTheDocument()
  })

  it('renders actions when provided', () => {
    render(
      <SectionHeader
        title="Title"
        actions={<button>Action</button>}
      />
    )
    expect(screen.getByRole('button', { name: 'Action' })).toBeInTheDocument()
  })

  it('applies accent style when accent is true', () => {
    const { container } = render(<SectionHeader title="Accented" accent />)
    const header = container.querySelector('.pl-3')
    expect(header).toBeInTheDocument()
  })
})

describe('EmptyState', () => {
  it('renders title and description', () => {
    render(<EmptyState title="No Data" description="Nothing to show here" />)
    expect(screen.getByText('No Data')).toBeInTheDocument()
    expect(screen.getByText('Nothing to show here')).toBeInTheDocument()
  })

  it('renders action when provided', () => {
    render(
      <EmptyState
        title="No Data"
        description="Nothing here"
        action={<button>Add Item</button>}
      />
    )
    expect(screen.getByRole('button', { name: 'Add Item' })).toBeInTheDocument()
  })

  it('renders icon when provided', () => {
    render(
      <EmptyState
        title="No Data"
        description="Nothing"
        icon={<span data-testid="empty-icon">Icon</span>}
      />
    )
    expect(screen.getByTestId('empty-icon')).toBeInTheDocument()
  })
})

describe('StatGrid', () => {
  it('renders children', () => {
    render(
      <StatGrid>
        <div>Card 1</div>
        <div>Card 2</div>
      </StatGrid>
    )
    expect(screen.getByText('Card 1')).toBeInTheDocument()
    expect(screen.getByText('Card 2')).toBeInTheDocument()
  })

  it('applies correct grid classes for different column counts', () => {
    const { container: cols2 } = render(<StatGrid columns={2}><div /></StatGrid>)
    expect(cols2.querySelector('.grid')).toHaveClass('grid-cols-2')

    const { container: cols3 } = render(<StatGrid columns={3}><div /></StatGrid>)
    expect(cols3.querySelector('.grid')).toHaveClass('grid-cols-2', 'lg:grid-cols-3')

    const { container: cols4 } = render(<StatGrid columns={4}><div /></StatGrid>)
    expect(cols4.querySelector('.grid')).toHaveClass('grid-cols-2', 'lg:grid-cols-4')
  })
})
