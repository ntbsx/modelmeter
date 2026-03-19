import { useState } from 'react'

type PageLoadingProps = {
  title: string
  subtitle?: string
  cards?: number
}

const loadingMessages = [
  'Gathering your data...',
  'Preparing your view...',
  'Crunching the numbers...',
  'Loading usage metrics...',
  'Syncing sources...',
]

function getLoadingMessage() {
  return loadingMessages[Math.floor(Math.random() * loadingMessages.length)]
}

export default function PageLoading({ title, subtitle, cards = 3 }: PageLoadingProps) {
  const cardsClass = cards >= 4 ? 'lg:grid-cols-4' : cards === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-3'
  const [message] = useState(getLoadingMessage)

  return (
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto w-full min-w-0">
      <div className="mb-8 sm:mb-10 space-y-2 animate-pulse">
        <div className="h-8 w-52 rounded bg-[var(--surface-tertiary)]" />
        <div className="h-4 w-72 max-w-full rounded bg-[var(--surface-secondary)]" />
      </div>

      <div className="mb-8 sm:mb-10 text-sm text-[var(--text-tertiary)] animate-pulse">
        <span className="font-medium text-[var(--text-secondary)]">{title}</span>
        {subtitle ? <span> · {subtitle}</span> : null}
        <span className="ml-2 opacity-60">· {message}</span>
      </div>

      <div className={`grid grid-cols-2 ${cardsClass} gap-4 sm:gap-5 mb-8 sm:mb-10`}>
        {Array.from({ length: cards }).map((_, index) => (
          <div
            key={`card-${index}`}
            className="ds-surface animate-pulse"
            style={{ animationDelay: `${index * 100}ms` }}
          >
            <div className="h-3.5 w-16 rounded bg-[var(--surface-tertiary)] mb-3" />
            <div className="h-7 w-24 rounded bg-[var(--surface-secondary)]" />
          </div>
        ))}
      </div>

      <div className="ds-surface overflow-hidden">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={`row-${index}`}
            className="px-4 sm:px-6 py-4 border-b border-[var(--border-subtle)] last:border-0 animate-pulse"
            style={{ animationDelay: `${(index + cards) * 50}ms` }}
          >
            <div className="h-4 w-3/5 rounded bg-[var(--surface-secondary)]" />
          </div>
        ))}
      </div>
    </div>
  )
}
