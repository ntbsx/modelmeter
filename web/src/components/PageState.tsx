import { AlertCircle, Inbox } from 'lucide-react'
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
      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 sm:p-8 shadow-sm">
        <div className="flex items-start gap-3">
          <Inbox className="h-5 w-5 text-gray-400 dark:text-gray-500 mt-0.5" />
          <div>
            <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{title}</h2>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">{description}</p>
            {action ? <div className="mt-4">{action}</div> : null}
          </div>
        </div>
      </div>
    </div>
  )
}
