import { useQuery } from '@tanstack/react-query'
import { CheckCircle, XCircle, AlertCircle, Key, RefreshCw } from 'lucide-react'
import { fetchApi } from '../lib/api'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'

type ProviderRateLimits = {
  requests_limit: number | null
  requests_remaining: number | null
  tokens_limit: number | null
  tokens_remaining: number | null
}

type ProviderStatus = {
  provider: string
  configured: boolean
  status: string
  models_count: number | null
  models: string[]
  rate_limits: ProviderRateLimits | null
  error: string | null
}

type ProvidersUsageResponse = {
  providers: ProviderStatus[]
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic: 'Anthropic (Claude)',
  openai: 'OpenAI',
}

const PROVIDER_ENV_VARS: Record<string, string> = {
  anthropic: 'MODELMETER_ANTHROPIC_API_KEY',
  openai: 'MODELMETER_OPENAI_API_KEY',
}

function StatusIcon({ status }: { status: string }) {
  if (status === 'ok') return <CheckCircle className="w-5 h-5 text-green-500" />
  if (status === 'error') return <XCircle className="w-5 h-5 text-red-500" />
  return <AlertCircle className="w-5 h-5 text-gray-400" />
}

function RateLimitBar({ label, used, limit }: { label: string; used: number | null; limit: number | null }) {
  if (limit === null || used === null) return null
  const remaining = used
  const pct = Math.min(100, Math.round(((limit - remaining) / limit) * 100))
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-gray-500 dark:text-gray-400">
        <span>{label}</span>
        <span>{remaining.toLocaleString()} / {limit.toLocaleString()} remaining</span>
      </div>
      <div className="h-1.5 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${100 - pct}%` }}
        />
      </div>
    </div>
  )
}

function ProviderCard({ provider }: { provider: ProviderStatus }) {
  const label = PROVIDER_LABELS[provider.provider] ?? provider.provider
  const envVar = PROVIDER_ENV_VARS[provider.provider]

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-6 space-y-4 transition-colors">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <StatusIcon status={provider.status} />
          <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100">{label}</h2>
        </div>
        {provider.configured && (
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded-full ${
              provider.status === 'ok'
                ? 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
                : 'bg-red-100 text-red-700 dark:bg-red-900/40 dark:text-red-400'
            }`}
          >
            {provider.status === 'ok' ? 'Connected' : 'Error'}
          </span>
        )}
      </div>

      {!provider.configured && (
        <div className="rounded-lg bg-gray-50 dark:bg-gray-800/50 border border-dashed border-gray-300 dark:border-gray-700 p-4 text-sm text-gray-500 dark:text-gray-400 space-y-1">
          <p>No API key configured.</p>
          {envVar && (
            <p>
              Set{' '}
              <code className="bg-gray-200 dark:bg-gray-700 rounded px-1 py-0.5 text-xs font-mono">
                {envVar}
              </code>{' '}
              to enable provider status checks.
            </p>
          )}
        </div>
      )}

      {provider.error && (
        <div className="rounded-lg bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 p-3 text-sm text-red-700 dark:text-red-400">
          {provider.error}
        </div>
      )}

      {provider.status === 'ok' && (
        <>
          {provider.models_count !== null && (
            <div className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-300">
              <Key className="w-4 h-4 text-gray-400" />
              <span>
                <span className="font-semibold text-gray-900 dark:text-gray-100">
                  {provider.models_count}
                </span>{' '}
                models available
              </span>
            </div>
          )}

          {provider.rate_limits && (
            <div className="space-y-3 pt-1">
              <div className="text-xs font-medium text-gray-500 dark:text-gray-400 uppercase tracking-wider">
                Rate Limits
              </div>
              <RateLimitBar
                label="Requests"
                used={provider.rate_limits.requests_remaining}
                limit={provider.rate_limits.requests_limit}
              />
              <RateLimitBar
                label="Tokens"
                used={provider.rate_limits.tokens_remaining}
                limit={provider.rate_limits.tokens_limit}
              />
              {provider.rate_limits.requests_limit === null &&
                provider.rate_limits.tokens_limit === null && (
                  <p className="text-xs text-gray-400 dark:text-gray-500">
                    Rate limit info not returned by this provider.
                  </p>
                )}
            </div>
          )}

          {provider.models.length > 0 && (
            <details className="group">
              <summary className="cursor-pointer text-sm text-blue-600 dark:text-blue-400 hover:underline list-none flex items-center gap-1 select-none">
                <span className="group-open:hidden">Show models</span>
                <span className="hidden group-open:inline">Hide models</span>
              </summary>
              <div className="mt-3 flex flex-wrap gap-1.5">
                {provider.models.map((m) => (
                  <span
                    key={m}
                    className="text-xs bg-gray-100 dark:bg-gray-800 text-gray-700 dark:text-gray-300 rounded px-2 py-0.5 font-mono"
                  >
                    {m}
                  </span>
                ))}
              </div>
            </details>
          )}
        </>
      )}
    </div>
  )
}

export default function ProviderUsage() {
  const { data, isLoading, isError, refetch, isFetching } = useQuery<ProvidersUsageResponse>({
    queryKey: ['provider-usage'],
    queryFn: () => fetchApi('/provider-usage'),
    staleTime: 30_000,
    retry: false,
  })

  if (isLoading) {
    return <PageLoading title="Provider Usage" subtitle="Checking API provider status" cards={2} />
  }

  if (isError || !data) {
    return (
      <PageErrorState
        title="Unable to load provider status"
        description="Could not fetch API provider status. Try refreshing the page."
      />
    )
  }

  return (
    <div className="px-4 py-6 sm:p-8 max-w-4xl mx-auto space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Provider Usage</h1>
          <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
            Live status and rate limits from your configured AI provider API keys.
          </p>
        </div>
        <button
          onClick={() => void refetch()}
          disabled={isFetching}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm border border-gray-200 dark:border-gray-700 text-gray-600 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-800 transition-colors disabled:opacity-50"
        >
          <RefreshCw className={`w-4 h-4 ${isFetching ? 'animate-spin' : ''}`} />
          Refresh
        </button>
      </div>

      <div className="grid gap-4 sm:grid-cols-1 lg:grid-cols-2">
        {data.providers.map((p) => (
          <ProviderCard key={p.provider} provider={p} />
        ))}
      </div>
    </div>
  )
}
