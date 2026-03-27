import { type FormEvent, useMemo, useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Globe, Database, ChevronDown, Server, Lock, Unlock, CheckCircle2, XCircle, AlertCircle, Plus, RefreshCw } from 'lucide-react'
import { fetchApi } from '../lib/api'
import type { DataSourcePublic, SourceHealth, SourceRegistryPublic } from '../types'
import PageLoading from '../components/PageLoading'
import { PageErrorState } from '../components/PageState'
import { Badge } from '../components/ui'
import { AgentBadge } from '../components/AgentBadge'

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

// Source type color configuration
const SOURCE_TYPE_CONFIG = {
  http: {
    icon: Globe,
    color: 'var(--accent-primary)',
    bgColor: 'var(--accent-primary-muted)',
    label: 'HTTP API',
  },
  sqlite: {
    icon: Database,
    color: 'var(--color-info)',
    bgColor: 'var(--color-info-muted)',
    label: 'SQLite',
  },
} as const

type SourceCardProps = {
  source: DataSourcePublic
  health: { is_reachable: boolean; error?: string; checked_at: string } | undefined
  onEdit: (source: DataSourcePublic) => void
  onRemove: (source: DataSourcePublic) => void
  animationDelay?: number
}

function SourceCard({ source, health, onEdit, onRemove, animationDelay = 0 }: SourceCardProps) {
  const [expanded, setExpanded] = useState(false)
  const typeConfig = SOURCE_TYPE_CONFIG[source.kind]
  const TypeIcon = typeConfig.icon
  const connectionTarget = source.kind === 'sqlite' ? String(source.db_path ?? '-') : String(source.base_url ?? '-')

  return (
    <article
      className="ds-surface flex flex-col transition-all duration-200 hover:-translate-y-0.5 hover:shadow-md animate-slide-up"
      style={{
        borderTop: `3px solid ${typeConfig.color}`,
        animationDelay: `${animationDelay}ms`,
      }}
    >
      {/* Card header */}
      <div className="p-5 pb-4">
        <div className="flex items-start justify-between gap-3">
          <div className="flex items-start gap-3 min-w-0 flex-1">
            {/* Source type icon */}
            <div
              className="shrink-0 w-10 h-10 rounded-xl flex items-center justify-center"
              style={{ backgroundColor: typeConfig.bgColor }}
            >
              <TypeIcon className="w-5 h-5" style={{ color: typeConfig.color }} />
            </div>

            <div className="min-w-0 flex-1">
              {/* Source ID as title */}
              <h3 className="ds-text-subheading font-semibold text-[var(--text-primary)] truncate" title={source.source_id}>
                {source.source_id}
              </h3>
              {/* Label as subtitle */}
              {source.label ? (
                <p className="ds-text-muted text-sm truncate mt-0.5" title={source.label}>{source.label}</p>
              ) : null}
            </div>
          </div>

          {/* Status badges */}
          <div className="flex flex-col items-end gap-1.5 shrink-0">
            <Badge variant={source.enabled ? 'success' : 'default'} className="text-xs">
              {source.enabled ? (
                <>
                  <Unlock className="w-3 h-3 mr-1" />
                  Enabled
                </>
              ) : (
                <>
                  <Lock className="w-3 h-3 mr-1" />
                  Disabled
                </>
              )}
            </Badge>
            <span className="ds-badge ds-badge-default text-xs" style={{ backgroundColor: typeConfig.bgColor, color: typeConfig.color }}>
              {typeConfig.label}
            </span>
            <AgentBadge agent={source.agent} />
          </div>
        </div>
      </div>

      {/* Health + connection info */}
      <div className="px-5 pb-4">
        <div className="flex items-center gap-3 mb-3">
          {/* Health indicator */}
          <div className="flex items-center gap-2">
            {health ? (
              health.is_reachable ? (
                <CheckCircle2 className="w-4 h-4 text-[var(--color-success)]" />
              ) : (
                <XCircle className="w-4 h-4 text-[var(--color-error)]" />
              )
            ) : (
              <AlertCircle className="w-4 h-4 text-[var(--text-tertiary)]" />
            )}
            <span className={`text-sm font-medium ${
              health
                ? health.is_reachable
                  ? 'text-[var(--color-success)]'
                  : 'text-[var(--color-error)]'
                : 'text-[var(--text-tertiary)]'
            }`}>
              {health
                ? health.is_reachable
                  ? 'Healthy'
                  : 'Unreachable'
                : 'Not checked'}
            </span>
          </div>

          {/* Connection target */}
          <div className="flex-1 min-w-0">
            <p className="ds-text-mono text-xs text-[var(--text-secondary)] truncate" title={connectionTarget}>
              {connectionTarget}
            </p>
          </div>

          {/* Credentials (HTTP only) */}
          {source.kind === 'http' && (
            source.has_auth ? (
              <Badge variant="success" className="text-xs shrink-0">
                <Lock className="w-3 h-3 mr-1" />
                Configured
              </Badge>
            ) : (
              <Badge variant="warning" className="text-xs shrink-0">
                <Unlock className="w-3 h-3 mr-1" />
                None
              </Badge>
            )
          )}
        </div>

        {/* Error details (expandable) */}
        {(health?.error || expanded) && (
          <button
            type="button"
            onClick={() => setExpanded(!expanded)}
            className="w-full flex items-center justify-between py-2 px-3 rounded-lg bg-[var(--color-error-muted)]/20 hover:bg-[var(--color-error-muted)]/30 transition-colors duration-150 focus-ring focus:outline-none"
          >
            <span className="text-xs text-[var(--color-error)] flex items-center gap-2">
              <AlertCircle className="w-3.5 h-3.5" />
              {expanded ? 'Hide error details' : 'View error details'}
            </span>
            <ChevronDown className={`w-3.5 h-3.5 text-[var(--color-error)] transition-transform duration-200 ${expanded ? 'rotate-180' : ''}`} />
          </button>
        )}

        {/* Expanded error */}
        {expanded && health?.error && (
          <div className="mt-2 p-2.5 rounded-lg bg-[var(--color-error-muted)]/20 animate-fade-in">
            <p className="text-xs text-[var(--color-error)] break-all">{health.error}</p>
          </div>
        )}
      </div>

      {/* Card actions */}
      <div className="mt-auto px-5 py-3 border-t border-[var(--border-subtle)] flex items-center justify-end gap-1 bg-[var(--surface-secondary)]/30 rounded-b-xl">
        <button
          type="button"
          onClick={() => onEdit(source)}
          className="ds-btn-ghost text-xs py-1.5 px-2 focus-ring"
          aria-label={`Edit ${source.source_id}`}
        >
          Edit
        </button>
        <button
          type="button"
          onClick={() => onRemove(source)}
          className="ds-btn-ghost text-xs py-1.5 px-2 text-[var(--color-error)] hover:bg-[var(--color-error-muted)] focus-ring"
          aria-label={`Remove ${source.source_id}`}
        >
          Remove
        </button>
      </div>
    </article>
  )
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
            <div className="ds-surface flex flex-col items-center justify-center py-16 px-6 text-center animate-fade-in">
              <div className="w-14 h-14 rounded-2xl bg-[var(--surface-tertiary)] flex items-center justify-center mb-4">
                <Server className="w-7 h-7 text-[var(--text-tertiary)]" />
              </div>
              <h3 className="ds-text-heading text-[var(--text-primary)] mb-1.5">No sources configured yet.</h3>
              <p className="ds-text-muted max-w-sm mb-6">
                Connect a local SQLite database or a remote HTTP endpoint to start tracking your AI usage.
              </p>
              <button type="button" onClick={onAddNew} className="ds-btn-primary">
                <Plus className="w-4 h-4 mr-2" />
                Add Your First Source
              </button>
            </div>
          ) : (
            <div className="space-y-4">
              {/* Source count header */}
              <div className="flex items-center justify-between">
                <p className="ds-text-label text-[var(--text-tertiary)]">
                  {(registry.sources ?? []).length} source{(registry.sources ?? []).length !== 1 ? 's' : ''} configured
                </p>
                <button
                  type="button"
                  onClick={() => checkMutation.mutate()}
                  disabled={checkMutation.isPending}
                  className="ds-btn-ghost text-sm"
                >
                  <RefreshCw className={`w-3.5 h-3.5 mr-1.5 ${checkMutation.isPending ? 'animate-spin' : ''}`} />
                  {checkMutation.isPending ? 'Checking...' : 'Check All Health'}
                </button>
              </div>

              {/* Source cards */}
              <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
                {(registry.sources ?? []).map((source, index) => (
                  <SourceCard
                    key={source.source_id}
                    source={source}
                    health={storedHealth[source.source_id]}
                    onEdit={onEdit}
                    onRemove={setDeleteTarget}
                    animationDelay={Math.min(index, 5) * 50}
                  />
                ))}
              </div>
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
