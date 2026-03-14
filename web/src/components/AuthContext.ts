import { createContext } from 'react'

export type AuthState = {
  /** Whether the backend requires authentication. null = still checking. */
  authRequired: boolean | null
  /** Whether the user is currently authenticated. */
  isAuthenticated: boolean
  /** Base64-encoded credentials string, or null. */
  credentials: string | null
  /** Attempt login with username/password. Returns null on success, error message on failure. */
  login: (username: string, password: string) => Promise<string | null>
  /** Clear stored credentials and mark as unauthenticated. */
  logout: () => void
}

export const AuthContext = createContext<AuthState | null>(null)
