import { useCallback, useEffect, useState, type ReactNode } from 'react'
import { AuthContext } from './AuthContext'

const STORAGE_KEY = 'modelmeter-auth'

type HealthResponse = {
  status: string
  app_version?: string
  auth_required?: boolean
}

type ProbeHealthResult =
  | { status: 'ok'; authRequired: boolean }
  | { status: 'error' }

function encodeBasicToken(username: string, password: string): string {
  const bytes = new TextEncoder().encode(`${username}:${password}`)
  let binary = ''
  for (const byte of bytes) {
    binary += String.fromCharCode(byte)
  }
  return btoa(binary)
}

async function probeHealth(): Promise<ProbeHealthResult> {
  try {
    const response = await fetch('/health')
    if (!response.ok) return { status: 'error' }
    const data: HealthResponse = await response.json()
    return { status: 'ok', authRequired: data.auth_required === true }
  } catch {
    return { status: 'error' }
  }
}

async function verifyCredentials(credentials: string): Promise<boolean> {
  try {
    const response = await fetch('/api/doctor', {
      headers: { Authorization: `Basic ${credentials}` },
    })
    return response.ok
  } catch {
    return false
  }
}

export function AuthProvider({ children }: { children: ReactNode }) {
  const [authRequired, setAuthRequired] = useState<boolean | null>(null)
  const [isAuthenticated, setIsAuthenticated] = useState(false)
  const [credentials, setCredentials] = useState<string | null>(null)

  useEffect(() => {
    let cancelled = false

    async function init() {
      const probe = await probeHealth()

      if (cancelled) return

      if (probe.status === 'ok' && !probe.authRequired) {
        setAuthRequired(false)
        setIsAuthenticated(true)
        return
      }

      setAuthRequired(true)

      const stored = localStorage.getItem(STORAGE_KEY)
      if (stored) {
        const valid = await verifyCredentials(stored)
        if (cancelled) return
        if (valid) {
          setCredentials(stored)
          setIsAuthenticated(true)
          return
        }
        localStorage.removeItem(STORAGE_KEY)
      }

      setIsAuthenticated(false)
    }

    init()
    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (username: string, password: string): Promise<string | null> => {
    try {
      const token = encodeBasicToken(username, password)
      const response = await fetch('/api/doctor', {
        headers: { Authorization: `Basic ${token}` },
      })
      if (!response.ok) {
        return 'Invalid username or password'
      }
      localStorage.setItem(STORAGE_KEY, token)
      setCredentials(token)
      setIsAuthenticated(true)
      return null
    } catch {
      return 'Unable to reach the server'
    }
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setCredentials(null)
    setIsAuthenticated(false)
  }, [])

  return (
    <AuthContext.Provider value={{ authRequired, isAuthenticated, credentials, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}
