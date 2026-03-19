import { type ReactNode, type KeyboardEvent } from 'react'

type TableColumn<T> = {
  key: keyof T | string
  header: string
  render?: (row: T) => ReactNode
  align?: 'left' | 'center' | 'right'
  className?: string
}

type DataTableProps<T> = {
  columns: TableColumn<T>[]
  data: T[]
  keyExtractor: (row: T) => string
  emptyMessage?: string
  className?: string
  onRowClick?: (row: T) => void
}

export function DataTable<T>({
  columns,
  data,
  keyExtractor,
  emptyMessage = 'No data available',
  className = '',
  onRowClick,
}: DataTableProps<T>) {
  const alignClasses = {
    left: 'text-left',
    center: 'text-center',
    right: 'text-right',
  }

  return (
    <div className={`ds-surface overflow-hidden ${className}`}>
      <div className="overflow-x-auto">
        <table className="ds-table w-full">
          <thead>
            <tr className="border-b border-[var(--border-default)]">
              {columns.map((col) => (
                <th
                  key={String(col.key)}
                  className={`px-4 sm:px-6 py-4 font-medium text-[var(--text-secondary)] whitespace-nowrap ${col.align ? alignClasses[col.align] : ''} ${col.className || ''}`}
                >
                  {col.header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-[var(--border-subtle)]">
            {data.length === 0 ? (
              <tr>
                <td colSpan={columns.length} className="px-4 sm:px-6 py-12 text-center text-[var(--text-tertiary)]">
                  {emptyMessage}
                </td>
              </tr>
            ) : (
              data.map((row) => (
                <tr
                  key={keyExtractor(row)}
                  className={`transition-colors hover:bg-[var(--surface-accent)]/50 outline-none focus-visible:outline-2 focus-visible:outline-[var(--accent-primary)] ${onRowClick ? 'cursor-pointer' : ''}`}
                  onClick={() => onRowClick?.(row)}
                  {...(onRowClick
                    ? {
                        tabIndex: 0,
                        onKeyDown: (e: KeyboardEvent<HTMLTableRowElement>) => {
                          if (e.key === 'Enter' || e.key === ' ' || e.code === 'Space') {
                            e.preventDefault()
                            onRowClick(row)
                          }
                        },
                      }
                    : {})}
                >
                  {columns.map((col) => (
                    <td
                      key={String(col.key)}
                      className={`px-4 sm:px-6 py-4 text-[var(--text-primary)] ${col.align ? alignClasses[col.align] : ''} ${col.className || ''}`}
                    >
                      {col.render ? col.render(row) : String((row as Record<string, unknown>)[col.key as string] ?? '')}
                    </td>
                  ))}
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}

type PageHeaderProps = {
  title: string
  description?: string
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, description, actions, className = '' }: PageHeaderProps) {
  return (
    <div className={`flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8 sm:mb-10 ${className}`}>
      <div>
        <h1 className="ds-text-heading">{title}</h1>
        {description && (
          <p className="mt-2 text-[var(--text-tertiary)]">{description}</p>
        )}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}

type SectionHeaderProps = {
  title: string
  description?: string
  actions?: ReactNode
  className?: string
  accent?: boolean
}

const sectionAccentStyles = {
  true: 'pl-3 border-l-2 border-l-[var(--accent-primary)]',
  false: '',
}

export function SectionHeader({ title, description, actions, className = '', accent = false }: SectionHeaderProps) {
  return (
    <div className={`flex flex-col sm:flex-row sm:items-start sm:justify-between gap-3 ${className}`}>
      <div className={sectionAccentStyles[accent.toString() as 'true' | 'false']}>
        <h2 className="ds-text-subheading">{title}</h2>
        {description && (
          <p className="mt-1 text-sm text-[var(--text-tertiary)]">{description}</p>
        )}
      </div>
      {actions && <div className="flex gap-2">{actions}</div>}
    </div>
  )
}

type EmptyStateProps = {
  title: string
  description: string
  action?: ReactNode
  icon?: ReactNode
}

export function EmptyState({ title, description, action, icon }: EmptyStateProps) {
  return (
    <div className="ds-surface p-8 sm:p-12 text-center">
      {icon && (
        <div className="mb-4 flex justify-center text-[var(--text-tertiary)]">
          {icon}
        </div>
      )}
      <h3 className="font-semibold text-[var(--text-primary)]">{title}</h3>
      <p className="mt-1 text-sm text-[var(--text-tertiary)]">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

type StatGridProps = {
  children: ReactNode
  columns?: 2 | 3 | 4
  className?: string
}

const gridClasses = {
  2: 'grid-cols-2',
  3: 'grid-cols-2 lg:grid-cols-3',
  4: 'grid-cols-2 lg:grid-cols-4',
}

export function StatGrid({ children, columns = 3, className = '' }: StatGridProps) {
  return (
    <div className={`grid ${gridClasses[columns]} gap-4 sm:gap-5 ${className}`}>
      {children}
    </div>
  )
}
