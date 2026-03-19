import { Suspense, lazy, useMemo } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import { Activity, BarChart2, FolderGit2, Building2, LogOut, Server, WifiOff, Zap } from 'lucide-react'
import { ThemeProvider } from './components/ThemeProvider'
import { ThemeToggle } from './components/ThemeToggle'
import { AuthProvider } from './components/AuthProvider'
import SourceScopePicker from './components/SourceScopePicker'
import DaysFilterPicker from './components/DaysFilterPicker'
import { useAuth } from './hooks/useAuth'
import { fetchApi } from './lib/api'
import type { SourceHealth } from './types'

const queryClient = new QueryClient()

const Overview = lazy(() => import('./pages/Overview'))
const Models = lazy(() => import('./pages/Models'))
const ModelDetail = lazy(() => import('./pages/ModelDetail'))
const Projects = lazy(() => import('./pages/Projects'))
const ProjectDetail = lazy(() => import('./pages/ProjectDetail'))
const Providers = lazy(() => import('./pages/Providers'))
const Live = lazy(() => import('./pages/Live'))
const Sources = lazy(() => import('./pages/Sources'))
const Login = lazy(() => import('./pages/Login'))

type HealthResponse = {
  status: string
  app_version?: string
  auth_required?: boolean
}

function VersionBadge({ className }: { className: string }) {
  const { data } = useQuery<HealthResponse>({
    queryKey: ['health-version'],
    queryFn: async () => {
      const response = await fetch('/health')
      if (!response.ok) {
        throw new Error(response.statusText)
      }
      return response.json() as Promise<HealthResponse>
    },
    staleTime: 60_000,
    retry: false,
  })

  if (!data?.app_version) {
    return null
  }

  return <span className={className}>v{data.app_version}</span>
}

const links = [
  { to: '/', icon: BarChart2, label: 'Overview' },
  { to: '/models', icon: Building2, label: 'Providers' },
  { to: '/projects', icon: FolderGit2, label: 'Projects' },
  { to: '/live', icon: Activity, label: 'Live' },
  { to: '/sources', icon: Server, label: 'Sources' },
]

function LogoutButton({ compact = false }: { compact?: boolean }) {
  const { authRequired, logout } = useAuth()

  if (!authRequired) return null

  const className = compact
    ? 'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)] transition-colors'
    : 'flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)] transition-colors w-full'

  return (
    <button
      onClick={logout}
      className={className}
      title="Sign out"
    >
      <LogOut className="w-4 h-4" />
      Sign out
    </button>
  )
}

function HeaderSourceStatus() {
  const { data, isLoading } = useQuery<SourceHealth[]>({
    queryKey: ['sources-health-check'],
    queryFn: () => fetchApi('/sources/check') as Promise<SourceHealth[]>,
    staleTime: 30_000,
    retry: 1,
  })

  const hasSources = (data?.length ?? 0) > 0

  if (isLoading) {
    return (
      <div 
        className="flex items-center gap-1.5 text-xs text-[var(--text-tertiary)]" 
        title="Checking source connectivity..."
      >
        <div className="w-3 h-3 rounded-full bg-[var(--text-tertiary)] animate-pulse" />
      </div>
    )
  }

  if (!hasSources) {
    return <div className="w-6" />
  }

  const failedSources = data?.filter(s => !s.is_reachable) ?? []
  const healthySources = data?.filter(s => s.is_reachable) ?? []
  
  if (failedSources.length === 0) {
    const sourceNames = healthySources.map(s => s.source_id).join(', ')
    return (
      <div 
        className="flex items-center gap-1 text-xs text-[var(--color-success)]" 
        title={`Federation active: ${sourceNames}`}
      >
        <Zap className="w-3 h-3" />
      </div>
    )
  }

  const failedNames = failedSources.map(s => s.source_id).join(', ')
  const healthyNames = healthySources.map(s => s.source_id).join(', ')
  const tooltip = failedNames 
    ? `Unreachable: ${failedNames}${healthyNames ? ` | Healthy: ${healthyNames}` : ''}`
    : 'Sources unreachable'

  return (
    <div className="flex items-center gap-1 text-xs" title={tooltip}>
      <WifiOff className="w-3 h-3 text-[var(--color-error)]" />
      <span className="text-[var(--color-error)] font-medium">
        {failedSources.length}
      </span>
    </div>
  )
}

function Nav() {
  const location = useLocation()

  return (
    <nav className="hidden lg:flex w-56 border-r border-[var(--border-default)] min-h-screen bg-[var(--surface-secondary)] p-4 flex-col">
      <div className="font-bold text-xl mb-8 px-4 text-[var(--accent-primary)] flex items-center gap-2.5">
        <Activity className="w-6 h-6" />
        ModelMeter
      </div>
      <div className="space-y-1 flex-1">
        {links.map((l) => {
          const Icon = l.icon
          return (
            <Link
              key={l.to}
              to={l.to}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                (location.pathname.startsWith(l.to) && l.to !== '/') || (l.to === '/' && location.pathname === '/')
                  ? 'bg-[var(--accent-primary-muted)] text-[var(--accent-primary-muted-foreground)] font-medium' 
                  : 'text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)]'
              }`}
            >
              <Icon className="w-5 h-5" />
              {l.label}
            </Link>
          )
        })}
      </div>
      <div className="border-t border-[var(--border-default)] pt-4 mt-4">
        <div className="px-4 text-xs text-[var(--text-tertiary)]">
          <VersionBadge className="text-xs text-[var(--text-tertiary)]" />
        </div>
      </div>
    </nav>
  )
}

function MobileNav() {
  const location = useLocation()
  const { authRequired, logout } = useAuth()

  return (
    <nav className="lg:hidden border-b border-[var(--border-default)] bg-[var(--surface-primary)]/80 backdrop-blur-sm">
      <div className="px-2 py-2 overflow-x-auto -mx-2">
        <div className="flex gap-1.5 min-w-max px-2">
          {links.map((l) => {
            const Icon = l.icon
            const isActive = (location.pathname.startsWith(l.to) && l.to !== '/') || (l.to === '/' && location.pathname === '/')

            return (
              <Link
                key={l.to}
                to={l.to}
                className={`inline-flex items-center gap-1.5 px-3 py-2.5 rounded-lg text-sm transition-colors min-h-[44px] ${
                  isActive
                    ? 'bg-[var(--accent-primary-muted)] text-[var(--accent-primary-muted-foreground)] font-medium'
                    : 'text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)]'
                }`}
              >
                <Icon className="w-4 h-4" />
                <span className="hidden sm:inline">{l.label}</span>
              </Link>
            )
          })}
          {authRequired && (
            <button
              onClick={logout}
              className="inline-flex items-center gap-1.5 px-3 py-2.5 rounded-lg text-sm transition-colors min-h-[44px] text-[var(--text-secondary)] hover:bg-[var(--surface-tertiary)] sm:hidden"
              aria-label="Sign out"
              title="Sign out"
            >
              <LogOut className="w-4 h-4" />
            </button>
          )}
        </div>
      </div>
    </nav>
  )
}

function AuthGate() {
  const { authRequired, isAuthenticated } = useAuth()
  const location = useLocation()

  const showDaysFilter = useMemo(() => {
    const path = location.pathname
    return path === '/' || 
           path === '/models' || 
           path.startsWith('/models/') || 
           path === '/projects'
  }, [location.pathname])

  if (authRequired === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--surface-secondary)]">
        <div className="text-[var(--text-tertiary)]">Loading...</div>
      </div>
    )
  }

  if (authRequired && !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex min-h-screen bg-[var(--surface-secondary)] text-[var(--text-primary)] transition-colors duration-200">
      <Nav />
      <div className="flex-1 min-w-0 flex flex-col min-h-screen overflow-x-hidden">
        <header className="h-14 lg:h-16 border-b border-[var(--border-default)] bg-[var(--surface-primary)]/80 backdrop-blur-sm flex items-center justify-between lg:justify-end px-4 lg:px-8 transition-colors duration-200 relative z-20">
          <div className="lg:hidden font-semibold text-[var(--accent-primary)] flex items-center gap-2">
            <Activity className="w-5 h-5" />
            ModelMeter
          </div>
          <div className="flex items-center gap-3">
            <SourceScopePicker />
            <HeaderSourceStatus />
            {showDaysFilter && <DaysFilterPicker />}
            <div className="hidden sm:block">
              <LogoutButton compact />
            </div>
            <ThemeToggle />
          </div>
        </header>
        <MobileNav />
        <main className="flex-1 bg-[var(--surface-secondary)]/50 transition-colors duration-200">
          <Suspense
            fallback={
              <div className="px-4 py-6 sm:p-8 text-[var(--text-tertiary)]">Loading page...</div>
            }
          >
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/models" element={<Providers />} />
              <Route path="/models/provider/:providerId" element={<Models />} />
              <Route path="/models/:modelId" element={<ModelDetail />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:projectId" element={<ProjectDetail />} />
              <Route path="/live" element={<Live />} />
              <Route path="/sources" element={<Sources />} />
              <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </Suspense>
        </main>
      </div>
    </div>
  )
}

function LoginRoute() {
  const { authRequired, isAuthenticated } = useAuth()

  if (authRequired === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-[var(--surface-secondary)]">
        <div className="text-[var(--text-tertiary)]">Loading...</div>
      </div>
    )
  }

  if (!authRequired || isAuthenticated) {
    return <Navigate to="/" replace />
  }

  return <Login />
}

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="modelmeter-theme">
      <QueryClientProvider client={queryClient}>
        <AuthProvider>
          <BrowserRouter>
            <Suspense
              fallback={
                <div className="min-h-screen flex items-center justify-center bg-[var(--surface-secondary)]">
                  <div className="text-[var(--text-tertiary)]">Loading...</div>
                </div>
              }
            >
              <Routes>
                <Route path="/login" element={<LoginRoute />} />
                <Route path="/*" element={<AuthGate />} />
              </Routes>
            </Suspense>
          </BrowserRouter>
        </AuthProvider>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
