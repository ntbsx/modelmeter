import { type FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import type { DataSourcePublic, SourceHealth, SourceRegistryPublic } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { Badge } from '../components/ui'

const HEALTH_STORAGE_KEY = 'modelmeter-source-health'

function loadStoredHealth(): Record<string, { is_reachable: boolean; error?: string; checked_at: string }> {
  try {
    const stored = localStorage.getItem(HEALTH_STORAGE_KEY)
    return stored ? JSON.parse(stored) : {}
  } catch {
    return {}
  }
}

function saveStoredHealth(health: Record<string, { is_reachable: boolean; error?: string; checked_at: string }>): void {
  try {
    localStorage.setItem(HEALTH_STORAGE_KEY, JSON.stringify(health))
  } catch {
    // ignore storage errors
  }
}

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
  kind: 'http',
  enabled: true,
  dbPath: '',
  baseUrl: '',
  username: '',
  password: '',
}

type StoredHealth = Record<string, { is_reachable: boolean; error?: string; checked_at: string }>

function sourceTarget(source: DataSourcePublic): string {
  return source.kind === 'sqlite' ? String(source.db_path ?? '-') : String(source.base_url ?? '-')
}

export default function Sources() {
  const queryClient = useQueryClient()
  const [form, setForm] = useState<SourceFormState>(EMPTY_FORM)
  const [editingSourceId, setEditingSourceId] = useState<string | null>(null)
  const [formError, setFormError] = useState<string | null>(null)
  const [showForm, setShowForm] = useState(false)
  const [deleteTarget, setDeleteTarget] = useState<DataSourcePublic | null>(null)
  const [storedHealth, setStoredHealth] = useState<StoredHealth>(() => loadStoredHealth())

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
      setShowForm(false)
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
      const healthMap: StoredHealth = {}
      for (const item of result) {
        healthMap[item.source_id] = {
          is_reachable: item.is_reachable,
          error: item.error ?? undefined,
          checked_at: new Date().toISOString(),
        }
      }
      setStoredHealth(healthMap)
      saveStoredHealth(healthMap)
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
    setShowForm(true)
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

  function onAddNew(): void {
    setShowForm(true)
    onReset()
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
    <div className="px-4 py-8 sm:px-8 sm:py-10 lg:py-12 max-w-6xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4 mb-8 sm:mb-10">
        <div>
          <h1 className="text-2xl sm:text-3xl font-bold tracking-tight text-[var(--text-primary)]">Sources</h1>
          <p className="mt-2 text-[var(--text-secondary)]">Manage local and remote analytics sources</p>
        </div>
        <div className="flex gap-2">
          <button
            type="button"
            onClick={onAddNew}
            className="ds-btn-primary"
          >
            Add Source
          </button>
          <button
            type="button"
            onClick={() => checkMutation.mutate()}
            disabled={checkMutation.isPending}
            className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-[var(--text-primary)] text-sm hover:bg-[var(--surface-tertiary)] disabled:opacity-50 transition-colors"
          >
            {checkMutation.isPending ? 'Checking...' : 'Run Health Check'}
          </button>
        </div>
      </div>

      {showForm && (
        <div className="bg-[var(--surface-primary)] rounded-xl border border-[var(--border-default)] shadow-sm p-5 sm:p-8">
          <h2 className="text-lg font-semibold text-[var(--text-primary)] mb-6">
            {editingSourceId ? `Edit Source: ${editingSourceId}` : 'Add Source'}
          </h2>
          <form onSubmit={onSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-5">
            <label className="text-sm font-medium text-[var(--text-primary)]">
              Source ID
              <input
                value={form.sourceId}
                onChange={(event) => setForm((prev) => ({ ...prev, sourceId: event.target.value }))}
                disabled={editingSourceId !== null}
                className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
                placeholder="local-macbook"
              />
            </label>
            <label className="text-sm font-medium text-[var(--text-primary)]">
              Label
              <input
                value={form.label}
                onChange={(event) => setForm((prev) => ({ ...prev, label: event.target.value }))}
                className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
                placeholder="My laptop"
              />
            </label>
            <label className="text-sm font-medium text-[var(--text-primary)]">
              Kind
              <select
                value={form.kind}
                onChange={(event) => setForm((prev) => ({ ...prev, kind: event.target.value as 'sqlite' | 'http' }))}
                className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
              >
                <option value="http">http</option>
                <option value="sqlite">sqlite</option>
              </select>
            </label>
            <label className="text-sm font-medium text-[var(--text-primary)] flex items-center gap-2 mt-7">
              <input
                type="checkbox"
                checked={form.enabled}
                onChange={(event) => setForm((prev) => ({ ...prev, enabled: event.target.checked }))}
                className="rounded"
              />
              Enabled
            </label>

            {form.kind === 'sqlite' ? (
              <label className="md:col-span-2 text-sm font-medium text-[var(--text-primary)]">
                SQLite DB Path
                <input
                  value={form.dbPath}
                  onChange={(event) => setForm((prev) => ({ ...prev, dbPath: event.target.value }))}
                  className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
                  placeholder="/Users/me/.local/share/opencode/opencode.db"
                />
              </label>
            ) : (
              <>
                <label className="md:col-span-2 text-sm font-medium text-[var(--text-primary)]">
                  Base URL
                  <input
                    value={form.baseUrl}
                    onChange={(event) => setForm((prev) => ({ ...prev, baseUrl: event.target.value }))}
                    className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
                    placeholder="https://modelmeter.example.com"
                  />
                </label>
                <label className="text-sm font-medium text-[var(--text-primary)]">
                  Username (optional)
                  <input
                    value={form.username}
                    onChange={(event) => setForm((prev) => ({ ...prev, username: event.target.value }))}
                    className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
                    placeholder="modelmeter"
                  />
                </label>
                <label className="text-sm font-medium text-[var(--text-primary)]">
                  Password (optional)
                  <input
                    type="password"
                    value={form.password}
                    onChange={(event) => setForm((prev) => ({ ...prev, password: event.target.value }))}
                    className="mt-1.5 w-full rounded-lg border border-[var(--border-default)] bg-[var(--surface-primary)] px-3 py-2 text-sm text-[var(--text-primary)]"
                  />
                </label>
              </>
            )}

            {formError ? <p className="md:col-span-2 text-sm text-red-600">{formError}</p> : null}

            <div className="md:col-span-2 flex gap-2 pt-2">
              <button
                type="submit"
                disabled={!canSubmit}
                className="ds-btn-primary"
              >
                {saveMutation.isPending ? 'Saving...' : editingSourceId ? 'Update Source' : 'Add Source'}
              </button>
              <button
                type="button"
                onClick={() => {
                  onReset()
                  setShowForm(false)
                }}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-[var(--text-primary)] text-sm transition-colors"
              >
                Cancel
              </button>
            </div>
          </form>
        </div>
      )}

      {!showForm && (
        <div>
          {(registry.sources ?? []).length === 0 ? (
            <div className="ds-surface p-8 sm:p-10 text-center">
              <p className="text-base font-medium text-[var(--text-primary)]">No sources configured yet.</p>
              <p className="mt-2 text-sm text-[var(--text-secondary)]">
                Add your local or remote source to start collecting analytics data.
              </p>
              <button type="button" onClick={onAddNew} className="ds-btn-secondary mt-5">
                Add Your First Source
              </button>
            </div>
          ) : (
            <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
              {(registry.sources ?? []).map((source) => {
                const result = storedHealth[source.source_id]
                const connectionTarget = sourceTarget(source)

                return (
                  <article
                    key={source.source_id}
                    className="ds-surface p-5 sm:p-6 transition-colors hover:bg-[var(--surface-accent)]/40"
                  >
                    <div className="flex flex-wrap items-start justify-between gap-3">
                      <div className="min-w-0 space-y-2">
                        <p className="text-base font-semibold text-[var(--text-primary)] break-all">{source.source_id}</p>
                        {source.label ? <p className="text-sm text-[var(--text-secondary)] break-all">{source.label}</p> : null}
                        <div className="flex flex-wrap items-center gap-2">
                          <Badge variant={source.kind === 'http' ? 'primary' : 'default'}>
                            {source.kind === 'http' ? 'HTTP API' : 'SQLite'}
                          </Badge>
                          <Badge variant={source.enabled ? 'success' : 'default'}>
                            {source.enabled ? 'Enabled' : 'Disabled'}
                          </Badge>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        <button
                          type="button"
                          onClick={() => onEdit(source)}
                          className="ds-btn-ghost"
                          aria-label={`Edit ${source.source_id}`}
                        >
                          Edit
                        </button>
                        <button
                          type="button"
                          onClick={() => setDeleteTarget(source)}
                          className="ds-btn-ghost text-[var(--color-error)] hover:bg-[var(--color-error-muted)]"
                          aria-label={`Remove ${source.source_id}`}
                        >
                          Remove
                        </button>
                      </div>
                    </div>

                    <div className="mt-5 grid grid-cols-1 gap-4 sm:grid-cols-2">
                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-tertiary)]">Connection</p>
                        <p className="mt-1 text-sm text-[var(--text-primary)] break-all" title={connectionTarget}>
                          {connectionTarget}
                        </p>
                      </div>

                      <div>
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-tertiary)]">Credentials</p>
                        <div className="mt-1">
                          {source.kind === 'http' ? (
                            <Badge variant={source.has_auth ? 'success' : 'warning'}>
                              {source.has_auth ? 'Configured' : 'None'}
                            </Badge>
                          ) : (
                            <span className="text-sm text-[var(--text-tertiary)]">N/A for SQLite</span>
                          )}
                        </div>
                      </div>

                      <div className="sm:col-span-2">
                        <p className="text-xs font-medium uppercase tracking-wide text-[var(--text-tertiary)]">Health</p>
                        <div className="mt-1.5 flex flex-wrap items-center gap-2">
                          {result ? (
                            <Badge variant={result.is_reachable ? 'success' : 'error'} dot>
                              {result.is_reachable ? 'Healthy' : 'Unreachable'}
                            </Badge>
                          ) : (
                            <span className="text-sm text-[var(--text-tertiary)]">No health check run yet</span>
                          )}
                          {result?.error ? <p className="text-sm text-[var(--color-error)] break-all">{result.error}</p> : null}
                        </div>
                      </div>
                    </div>
                  </article>
                )
              })}
            </div>
          )}
        </div>
      )}

      {deleteTarget && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
          <div className="bg-[var(--surface-primary)] rounded-xl shadow-xl max-w-md w-full mx-4 p-6">
            <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">Remove Source</h3>
            <p className="text-[var(--text-secondary)] mb-6">
              Are you sure you want to remove source <strong>{deleteTarget.source_id}</strong>? This action cannot be undone.
            </p>
            <div className="flex justify-end gap-3">
              <button
                type="button"
                onClick={() => setDeleteTarget(null)}
                className="px-4 py-2 rounded-lg border border-[var(--border-default)] text-[var(--text-primary)] text-sm"
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={() => {
                  removeMutation.mutate(deleteTarget.source_id)
                  setDeleteTarget(null)
                }}
                className="px-4 py-2 rounded-lg bg-red-600 text-white text-sm font-medium hover:bg-red-700"
              >
                Remove
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
