const API_BASE = import.meta.env.DEV ? '/api' : '/api'
const AUTH_STORAGE_KEY = 'modelmeter-auth'

function getAuthHeaders(): HeadersInit {
  const token = localStorage.getItem(AUTH_STORAGE_KEY)
  if (token) {
    return { Authorization: `Basic ${token}` }
  }
  return {}
}

export function buildApiUrl(endpoint: string, params?: Record<string, string | number>): string {
  const cleanEndpoint = endpoint.startsWith('/') ? endpoint : `/${endpoint}`
  const url = new URL(API_BASE + cleanEndpoint, window.location.origin)

  if (params) {
    Object.entries(params).forEach(([key, value]) => {
      url.searchParams.append(key, String(value))
    })
  }

  return url.toString()
}

type FetchApiOptions = {
  method?: 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE'
  body?: unknown
}

export async function fetchApi<T>(
  endpoint: string,
  params?: Record<string, string | number>,
  options?: FetchApiOptions
): Promise<T> {
  const url = buildApiUrl(endpoint, params)
  const method = options?.method ?? 'GET'

  const headers: HeadersInit = {
    ...getAuthHeaders(),
  }

  let body: string | undefined
  if (options?.body !== undefined) {
    headers['Content-Type'] = 'application/json'
    body = JSON.stringify(options.body)
  }

  const response = await fetch(url.toString(), {
    method,
    headers,
    body,
  })

  if (response.status === 401) {
    localStorage.removeItem(AUTH_STORAGE_KEY)
    window.location.href = '/login'
    throw new Error('Session expired')
  }

  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || response.statusText)
  }

  return response.json()
}

export function getAuthToken(): string | null {
  return localStorage.getItem(AUTH_STORAGE_KEY)
}
