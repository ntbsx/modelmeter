import { FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import type { DataSourcePublic, SourceHealth, SourceRegistryPublic } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'

type SourceFormState = {
  sourceId: string
  label: string
  kind: 'sqlite' | 'http'
  enabled: boolean
  dbPath: string
  baseUrl: string
  username: string
  password: string
}

const EMPTY_FORM: SourceFormState = {
  sourceId: '',
  label: '',
  kind: 'sqlite',
  enabled: true,
  dbPath: '',
  baseUrl: '',
  username: '',
  password: '',
}

function sourceTarget(source: DataSourcePublic): string {
  return source.kind === 'sqlite' ? String(source.db_path ?? '-') : String(source.base_url ?? '-')
}

export default function Sources() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<SourceFormState>(EMPTY_FORM)
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [health, setHealth] = useState<SourceHealth[] | null>(null)

  const {
    data: registry,
    isLoading,
    isError,
  } = useQuery<SourceRegistryPublic>({
    queryKey: ['sources-registry'],
    queryFn: () => fetchApi('/sources'),
  })

  const saveMutation = useMutation({
    mutationFn: async () => {
      const sourceId = form.sourceId.trim()
      if (!sourceId) {
        throw new Error('Source ID is required')
      }
      if (form.kind === 'sqlite' && !form.dbPath.trim()) {
        throw new Error('SQLite source requires a DB path')
      }
      if (form.kind === 'http' && !form.baseUrl.trim()) {
        throw new Error('HTTP source requires a base URL')
      }
      const hasUsername = form.username.trim().length > 0
      const hasPassword = form.password.length > 0
      if (hasUsername !== hasPassword) {
        throw new Error('Username and password must be provided together')
      }

      const auth = hasUsername && hasPassword
        ? { username: form.username.trim(), password: form.password }
        : null

      await fetchApi(`/sources/${encodeURIComponent(sourceId)}`, undefined, {
        method: 'PUT',
        body: {
          label: form.label.trim() || null,
          kind: form.kind,
          enabled: form.enabled,
          db_path: form.kind === 'sqlite' ? form.dbPath.trim() : null,
          base_url: form.kind === 'http' ? form.baseUrl.trim() : null,
          auth,
          preserve_existing_auth: true,
        },
      })
    },
    onSuccess: async () => {
      setForm(EMPTY_FORM)
      setEditingSourceId(null)
      setFormError(null)
      await queryClient.invalidateQueries({ queryKey: ['sources-registry'] })
    },
    onError: (error) => {
      setFormError(error instanceof Error ? error.message : 'Unable to save source')
    },
  })

  const removeMutation = useMutation({
    mutationFn: async (sourceId: string) => {
      await fetchApi(`/sources/${encodeURIComponent(sourceId)}`, undefined, { method: 'DELETE' })
    },
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ['sources-registry'] })
    },
  })

  const checkMutation = useMutation({
    mutationFn: async () => {
      const result = await fetchApi<SourceHealth[]>('/sources/check')
      setHealth(result)
    },
  })

  const canSubmit = useMemo(() => {
    if (saveMutation.isPending) return false
    if (!form.sourceId.trim()) return false
    if (form.kind === 'sqlite' && !form.dbPath.trim()) return false
    if (form.kind === 'http' && !form.baseUrl.trim()) return false
    return true
  }, [form, saveMutation.isPending])

  function onEdit(source: DataSourcePublic): void {
    setEditingSourceId(source.source_id)
    setFormError(null)
    setForm({
      sourceId: source.source_id,
      label: source.label ?? '',
      kind: source.kind,
      enabled: source.enabled,
      dbPath: source.kind === 'sqlite' ? String(source.db_path ?? '') : '',
      baseUrl: source.kind === 'http' ? String(source.base_url ?? '') : '',
      username: '',
      password: '',
    })
  }

  function onReset(): void {
    setForm(EMPTY_FORM)
    setEditingSourceId(null)
    setFormError(null)
  }

  function onSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setFormError(null)
    saveMutation.mutate()
  }

  if (isLoading) {
    return <PageLoading title="Sources" subtitle="Loading configured sources" cards={2} />
  }

  if (isError || !registry) {
    return (
      <PageErrorState
        title="Unable to load sources"
        description="We could not load source configuration right now. Try refreshing the page."
      />
    )
  }

  return (
    <div className="px-4 py-6 sm:p-8 max-w-6xl mx-auto space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-3">
        <div>
          <h1 className="text-xl sm:text-2xl font-bold text-gray-900 dark:text-white">Sources</h1>
          <p className="text-gray-500 dark:text-gray-400 mt-1">Manage local and remote analytics sources</p>
        </div>
        <button
          type="button"
          onClick={() => checkMutation.mutate()}
          disabled={checkMutation.isPending}
          className="px-3 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm text-gray-700 dark:text-gray-200 hover:bg-gray-100 dark:hover:bg-gray-800 disabled:opacity-50"
        >
          {checkMutation.isPending ? 'Checking...' : 'Run Health Check'}
        </button>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm p-4 sm:p-6">
        <h2 className="text-lg font-semibold text-gray-900 dark:text-gray-100 mb-4">
          {editingSourceId ? `Edit Source: ${editingSourceId}` : 'Add Source'}
        </h2>
        <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Source ID
            <input
              value={form.sourceId}
              onChange={(event) => setForm((prev) => ({ ...prev, sourceId: event.target.value }))}
              disabled={editingSourceId !== null}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
              placeholder="local-macbook"
            />
          </label>
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Label
            <input
              value={form.label}
              onChange={(event) => setForm((prev) => ({ ...prev, label: event.target.value }))}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
              placeholder="My laptop"
            />
          </label>
          <label className="text-sm text-gray-700 dark:text-gray-300">
            Kind
            <select
              value={form.kind}
              onChange={(event) => setForm((prev) => ({ ...prev, kind: event.target.value as 'sqlite' | 'http' }))}
              className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
            >
              <option value="sqlite">sqlite</option>
              <option value="http">http</option>
            </select>
          </label>
          <label className="text-sm text-gray-700 dark:text-gray-300 flex items-center gap-2 mt-6">
            <input
              type="checkbox"
              checked={form.enabled}
              onChange={(event) => setForm((prev) => ({ ...prev, enabled: event.target.checked }))}
            />
            Enabled
          </label>

          {form.kind === 'sqlite' ? (
            <label className="md:col-span-2 text-sm text-gray-700 dark:text-gray-300">
              SQLite DB Path
              <input
                value={form.dbPath}
                onChange={(event) => setForm((prev) => ({ ...prev, dbPath: event.target.value }))}
                className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
                placeholder="/Users/me/.local/share/opencode/opencode.db"
              />
            </label>
          ) : (
            <>
              <label className="md:col-span-2 text-sm text-gray-700 dark:text-gray-300">
                Base URL
                <input
                  value={form.baseUrl}
                  onChange={(event) => setForm((prev) => ({ ...prev, baseUrl: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
                  placeholder="https://modelmeter.example.com"
                />
              </label>
              <label className="text-sm text-gray-700 dark:text-gray-300">
                Username (optional)
                <input
                  value={form.username}
                  onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
                  placeholder="modelmeter"
                />
              </label>
              <label className="text-sm text-gray-700 dark:text-gray-300">
                Password (optional)
                <input
                  type="password"
                  value={form.password}
                  onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                  className="mt-1 w-full rounded-lg border border-gray-300 dark:border-gray-700 bg-white dark:bg-gray-950 px-3 py-2"
                />
              </label>
            </>
          )}

          {formError ? <p className="md:col-span-2 text-sm text-red-600">{formError}</p> : null}

          <div className="md:col-span-2 flex gap-2">
            <button
              type="submit"
              disabled={!canSubmit}
              className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
            >
              {saveMutation.isPending ? 'Saving...' : editingSourceId ? 'Update Source' : 'Add Source'}
            </button>
            {editingSourceId ? (
              <button
                type="button"
                onClick={onReset}
                className="px-4 py-2 rounded-lg border border-gray-300 dark:border-gray-700 text-sm"
              >
                Cancel
              </button>
            ) : null}
          </div>
        </form>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs sm:text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium">Source ID</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium">Kind</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium">Target</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium">Auth</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium">Enabled</th>
                <th className="px-3 sm:px-6 py-3 sm:py-4 font-medium text-right">Actions</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {registry.sources.map((source) => {
                const result = health?.find((item) => item.source_id === source.source_id)
                return (
                  <tr key={source.source_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                    <td className="px-3 sm:px-6 py-3 sm:py-4 font-medium">{source.source_id}</td>
                    <td className="px-3 sm:px-6 py-3 sm:py-4">{source.kind}</td>
                    <td className="px-3 sm:px-6 py-3 sm:py-4 text-gray-600 dark:text-gray-400">{sourceTarget(source)}</td>
                    <td className="px-3 sm:px-6 py-3 sm:py-4">{source.has_auth ? 'Configured' : 'None'}</td>
                    <td className="px-3 sm:px-6 py-3 sm:py-4">
                      <span className={source.enabled ? 'text-emerald-600' : 'text-gray-500'}>
                        {source.enabled ? 'Yes' : 'No'}
                      </span>
                    </td>
                    <td className="px-3 sm:px-6 py-3 sm:py-4 text-right space-x-2">
                      {result ? (
                        <span className={result.is_reachable ? 'text-emerald-600 text-xs' : 'text-red-600 text-xs'}>
                          {result.is_reachable ? 'Healthy' : 'Unreachable'}
                        </span>
                      ) : null}
                      <button
                        type="button"
                        onClick={() => onEdit(source)}
                        className="text-blue-600 hover:text-blue-800 text-xs"
                      >
                        Edit
                      </button>
                      <button
                        type="button"
                        onClick={() => {
                          if (!window.confirm(`Remove source '${source.source_id}'?`)) return
                          removeMutation.mutate(source.source_id)
                        }}
                        className="text-red-600 hover:text-red-800 text-xs"
                      >
                        Remove
                      </button>
                    </td>
                  </tr>
                )
              })}
              {registry.sources.length === 0 ? (
                <tr>
                  <td colSpan={6} className="px-3 sm:px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                    No sources configured yet.
                  </td>
                </tr>
              ) : null}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
