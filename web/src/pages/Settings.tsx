import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { CheckCircle, Eye, EyeOff, Lock, Save, Trash2 } from 'lucide-react'
import { fetchApi } from '../lib/api'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'

type SettingsKeyStatus = {
  configured: boolean
  source: 'env' | 'user' | null
}

type SettingsResponse = {
  anthropic_api_key: SettingsKeyStatus
  openai_api_key: SettingsKeyStatus
}

type SettingsUpdateRequest = {
  anthropic_api_key?: string | null
  openai_api_key?: string | null
}

async function putSettings(body: SettingsUpdateRequest): Promise<SettingsResponse> {
  const token = localStorage.getItem('modelmeter-auth')
  const headers: Record<string, string> = { 'Content-Type': 'application/json' }
  if (token) headers['Authorization'] = `Basic ${token}`
  const res = await fetch('/api/settings', {
    method: 'PUT',
    headers,
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error((err as { detail?: string }).detail ?? res.statusText)
  }
  return res.json() as Promise<SettingsResponse>
}

const PROVIDER_LABELS: Record<string, string> = {
  anthropic_api_key: 'Anthropic (Claude)',
  openai_api_key: 'OpenAI',
}

const PROVIDER_PLACEHOLDERS: Record<string, string> = {
  anthropic_api_key: 'sk-ant-...',
  openai_api_key: 'sk-...',
}

type ApiKeyFieldProps = {
  label: string
  fieldKey: 'anthropic_api_key' | 'openai_api_key'
  status: SettingsKeyStatus
  onSave: (key: string, value: string | null) => void
  saving: boolean
}

function ApiKeyField({ label, fieldKey, status, onSave, saving }: ApiKeyFieldProps) {
  const [value, setValue] = useState('')
  const [show, setShow] = useState(false)
  const [saved, setSaved] = useState(false)

  const isEnv = status.source === 'env'

  const handleSave = () => {
    if (!value.trim()) return
    onSave(fieldKey, value.trim())
    setValue('')
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleClear = () => {
    onSave(fieldKey, null)
    setValue('')
  }

  return (
    <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 p-6 space-y-4">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-base font-semibold text-gray-900 dark:text-gray-100">{label}</h2>
          <p className="text-xs text-gray-500 dark:text-gray-400 mt-0.5">
            {PROVIDER_LABELS[fieldKey]} API Key
          </p>
        </div>
        {status.configured && (
          <span
            className={`text-xs font-medium px-2.5 py-1 rounded-full ${
              isEnv
                ? 'bg-purple-100 text-purple-700 dark:bg-purple-900/40 dark:text-purple-400'
                : 'bg-green-100 text-green-700 dark:bg-green-900/40 dark:text-green-400'
            }`}
          >
            {isEnv ? 'Via environment' : 'Saved'}
          </span>
        )}
      </div>

      {isEnv ? (
        <div className="flex items-center gap-2 rounded-lg bg-purple-50 dark:bg-purple-900/20 border border-purple-200 dark:border-purple-800 px-3 py-2.5 text-sm text-purple-700 dark:text-purple-400">
          <Lock className="w-4 h-4 shrink-0" />
          <span>
            Set via <code className="font-mono bg-purple-100 dark:bg-purple-900/40 rounded px-1 text-xs">
              MODELMETER_{fieldKey.toUpperCase()}
            </code> environment variable. Remove the env var to manage it here.
          </span>
        </div>
      ) : (
        <div className="space-y-3">
          {status.configured && (
            <div className="flex items-center gap-2 text-sm text-gray-500 dark:text-gray-400">
              <CheckCircle className="w-4 h-4 text-green-500 shrink-0" />
              <span>API key is saved. Enter a new value below to replace it.</span>
            </div>
          )}
          <div className="flex gap-2">
            <div className="relative flex-1">
              <input
                type={show ? 'text' : 'password'}
                value={value}
                onChange={(e) => setValue(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && handleSave()}
                placeholder={
                  status.configured
                    ? 'Enter new key to replace…'
                    : PROVIDER_PLACEHOLDERS[fieldKey]
                }
                className="w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-800 px-3 py-2 pr-10 text-sm text-gray-900 dark:text-gray-100 placeholder-gray-400 dark:placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-blue-500 dark:focus:ring-blue-400"
              />
              <button
                type="button"
                onClick={() => setShow((s) => !s)}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                tabIndex={-1}
              >
                {show ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
              </button>
            </div>
            <button
              onClick={handleSave}
              disabled={!value.trim() || saving}
              className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium bg-blue-600 hover:bg-blue-700 text-white disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {saved ? (
                <CheckCircle className="w-4 h-4" />
              ) : (
                <Save className="w-4 h-4" />
              )}
              {saved ? 'Saved!' : 'Save'}
            </button>
            {status.configured && (
              <button
                onClick={handleClear}
                disabled={saving}
                className="inline-flex items-center gap-1.5 px-3 py-2 rounded-lg text-sm font-medium border border-red-300 dark:border-red-700 text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 disabled:opacity-40 transition-colors"
              >
                <Trash2 className="w-4 h-4" />
                Clear
              </button>
            )}
          </div>
        </div>
      )}
    </div>
  )
}

export default function Settings() {
  const queryClient = useQueryClient()

  const { data, isLoading, isError } = useQuery<SettingsResponse>({
    queryKey: ['settings'],
    queryFn: () => fetchApi('/settings'),
    staleTime: 0,
  })

  const { mutate, isPending } = useMutation({
    mutationFn: putSettings,
    onSuccess: (updated) => {
      queryClient.setQueryData(['settings'], updated)
      // Also invalidate provider-usage so it re-fetches with new keys
      void queryClient.invalidateQueries({ queryKey: ['provider-usage'] })
    },
  })

  const handleSave = (key: string, value: string | null) => {
    mutate({ [key]: value })
  }

  if (isLoading) {
    return <PageLoading title="Settings" subtitle="Loading current settings" cards={2} />
  }

  if (isError || !data) {
    return (
      <PageErrorState
        title="Unable to load settings"
        description="Could not fetch settings. Try refreshing the page."
      />
    )
  }

  return (
    <div className="px-4 py-6 sm:p-8 max-w-2xl mx-auto space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900 dark:text-gray-100">Settings</h1>
        <p className="text-sm text-gray-500 dark:text-gray-400 mt-1">
          Configure API keys for provider usage checks. Keys are stored locally on the server.
          Environment variables always take precedence.
        </p>
      </div>

      <div className="space-y-4">
        <h2 className="text-sm font-semibold text-gray-500 dark:text-gray-400 uppercase tracking-wider">
          API Keys
        </h2>
        <ApiKeyField
          label="Anthropic (Claude)"
          fieldKey="anthropic_api_key"
          status={data.anthropic_api_key}
          onSave={handleSave}
          saving={isPending}
        />
        <ApiKeyField
          label="OpenAI"
          fieldKey="openai_api_key"
          status={data.openai_api_key}
          onSave={handleSave}
          saving={isPending}
        />
      </div>
    </div>
  )
}
