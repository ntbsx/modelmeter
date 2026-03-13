const API_BASE = import.meta.env.DEV ? '/api' : '/api'

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

  const response = await fetch(url.toString())
  if (!response.ok) {
    const error = await response.json().catch(() => ({}))
    throw new Error(error.detail || response.statusText)
  }

  return response.json()
}
