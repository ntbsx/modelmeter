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

export async function fetchApi<T>(endpoint: string, params?: Record<string, string | number>): Promise<T> {
  const url = buildApiUrl(endpoint, params)

  const response = await fetch(url.toString(), {
    headers: getAuthHeaders(),
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
