type PageLoadingProps = {
  title: string
  subtitle?: string
  cards?: number
}

export default function PageLoading({ title, subtitle, cards = 3 }: PageLoadingProps) {
  const cardsClass = cards >= 4 ? 'sm:grid-cols-4' : cards === 2 ? 'sm:grid-cols-2' : 'sm:grid-cols-3'

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto w-full min-w-0 animate-pulse">
      <div className="mb-6 sm:mb-8 space-y-2">
        <div className="h-7 w-44 rounded bg-gray-200 dark:bg-gray-800" />
        <div className="h-4 w-72 max-w-full rounded bg-gray-100 dark:bg-gray-900" />
      </div>

      <div className="mb-6 text-sm text-gray-500 dark:text-gray-400">
        <span className="font-medium text-gray-600 dark:text-gray-300">{title}</span>
        {subtitle ? <span> · {subtitle}</span> : null}
      </div>

      <div className={`grid grid-cols-1 ${cardsClass} gap-4 mb-6`}>
        {Array.from({ length: cards }).map((_, index) => (
          <div
            key={`card-${index}`}
            className="bg-white dark:bg-gray-900 p-4 sm:p-6 rounded-xl border border-gray-200 dark:border-gray-800"
          >
            <div className="h-4 w-20 rounded bg-gray-200 dark:bg-gray-800 mb-3" />
            <div className="h-7 w-24 rounded bg-gray-100 dark:bg-gray-900" />
          </div>
        ))}
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 overflow-hidden">
        {Array.from({ length: 6 }).map((_, index) => (
          <div
            key={`row-${index}`}
            className="px-4 sm:px-6 py-4 border-b border-gray-100 dark:border-gray-800/70 last:border-0"
          >
            <div className="h-4 w-3/5 rounded bg-gray-100 dark:bg-gray-900" />
          </div>
        ))}
      </div>
    </div>
  )
}
