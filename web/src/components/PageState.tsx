import { AlertCircle, Inbox, Sparkles } from 'lucide-react'
import type { ReactNode } from 'react'

type PageStateProps = {
  title: string
  description: string
  action?: ReactNode
}

export function PageErrorState({ title, description, action }: PageStateProps) {
  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto">
      <div className="bg-red-50 dark:bg-red-900/15 border border-red-200 dark:border-red-800 rounded-xl p-6 sm:p-8">
        <div className="flex items-start gap-3">
          <AlertCircle className="h-5 w-5 text-red-600 dark:text-red-400 mt-0.5" />
          <div>
            <h2 className="text-lg font-semibold text-red-700 dark:text-red-300">{title}</h2>
            <p className="text-sm text-red-600/90 dark:text-red-200/90 mt-1">{description}</p>
            {action ? <div className="mt-4">{action}</div> : null}
          </div>
        </div>
      </div>
    </div>
  )
}

export function PageEmptyState({ title, description, action }: PageStateProps) {
  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto">
      <div className="ds-surface p-6 sm:p-8 text-center">
        <div className="inline-flex items-center justify-center w-12 h-12 rounded-full bg-[var(--surface-secondary)] mb-4">
          <Inbox className="h-6 w-6 text-[var(--text-tertiary)]" />
        </div>
        <h2 className="text-lg font-semibold text-[var(--text-primary)]">{title}</h2>
        <p className="text-sm text-[var(--text-secondary)] mt-1 max-w-sm mx-auto">{description}</p>
        {action ? <div className="mt-4">{action}</div> : null}
      </div>
    </div>
  )
}

type PageFirstTimeStateProps = {
  title: string
  description: string
  hint?: string
  action?: ReactNode
}

export function PageFirstTimeState({ title, description, hint, action }: PageFirstTimeStateProps) {
  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto">
      <div className="ds-surface p-8 sm:p-12 text-center">
        <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-gradient-to-br from-[var(--accent-primary)]/10 to-[var(--accent-primary)]/5 mb-5">
          <Sparkles className="h-8 w-8 text-[var(--accent-primary)]" />
        </div>
        <h2 className="text-xl font-semibold text-[var(--text-primary)]">{title}</h2>
        <p className="text-sm text-[var(--text-secondary)] mt-2 max-w-sm mx-auto">{description}</p>
        {hint && (
          <p className="text-xs text-[var(--text-tertiary)] mt-3 max-w-xs mx-auto">
            {hint}
          </p>
        )}
        {action && <div className="mt-6">{action}</div>}
      </div>
    </div>
  )
}
