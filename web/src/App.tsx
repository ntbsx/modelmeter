import { Suspense, lazy } from 'react'
import { QueryClient, QueryClientProvider, useQuery } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Link, Navigate, useLocation } from 'react-router-dom'
import { Activity, BarChart2, FolderGit2, Cpu, LogOut, Zap } from 'lucide-react'
import { ThemeProvider } from './components/ThemeProvider'
import { ThemeToggle } from './components/ThemeToggle'
import { AuthProvider } from './components/AuthProvider'
import { useAuth } from './hooks/useAuth'

const queryClient = new QueryClient()

const Overview = lazy(() => import('./pages/Overview'))
const Models = lazy(() => import('./pages/Models'))
const ModelDetail = lazy(() => import('./pages/ModelDetail'))
const Projects = lazy(() => import('./pages/Projects'))
const ProjectDetail = lazy(() => import('./pages/ProjectDetail'))
const Live = lazy(() => import('./pages/Live'))
const ProviderUsage = lazy(() => import('./pages/ProviderUsage'))
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
  { to: '/models', icon: Cpu, label: 'Models' },
  { to: '/projects', icon: FolderGit2, label: 'Projects' },
  { to: '/live', icon: Activity, label: 'Live' },
  { to: '/provider-usage', icon: Zap, label: 'Providers' },
]

function LogoutButton({ compact = false }: { compact?: boolean }) {
  const { authRequired, logout } = useAuth()

  if (!authRequired) return null

  const className = compact
    ? 'inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 transition-colors'
    : 'flex items-center gap-2 px-4 py-2 rounded-lg text-sm text-gray-500 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60 transition-colors w-full'

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

function Nav() {
  const location = useLocation()

  return (
    <nav className="hidden md:flex w-64 border-r border-gray-200 dark:border-gray-800 min-h-screen bg-gray-50/50 dark:bg-gray-900/50 p-4 flex-col">
      <div className="font-bold text-xl mb-8 px-4 text-blue-600 dark:text-blue-400 flex items-center gap-2">
        <Activity className="w-6 h-6" />
        ModelMeter
      </div>
      <div className="space-y-1 flex-1">
        {links.map((l) => {
          const Icon = l.icon
          const active = location.pathname === l.to
          return (
            <Link
              key={l.to}
              to={l.to}
              className={`flex items-center gap-3 px-4 py-2.5 rounded-lg transition-colors ${
                active 
                  ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 font-medium' 
                  : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60'
              }`}
            >
              <Icon className="w-5 h-5" />
              {l.label}
            </Link>
          )
        })}
      </div>
      <div className="space-y-2 border-t border-gray-200 dark:border-gray-800 pt-4">
        <LogoutButton />
        <div className="px-4 text-xs text-gray-400 dark:text-gray-500">
          <VersionBadge className="text-xs text-gray-400 dark:text-gray-500" />
        </div>
      </div>
    </nav>
  )
}

function MobileNav() {
  const location = useLocation()

  return (
    <nav className="md:hidden border-b border-gray-200 dark:border-gray-800 bg-white/95 dark:bg-gray-950/95 backdrop-blur">
      <div className="px-3 py-2 overflow-x-auto">
        <div className="flex gap-2 min-w-max">
          {links.map((l) => {
            const Icon = l.icon
            const active = location.pathname === l.to

            return (
              <Link
                key={l.to}
                to={l.to}
                className={`inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm transition-colors ${
                  active
                    ? 'bg-blue-100 text-blue-700 dark:bg-blue-900/40 dark:text-blue-400 font-medium'
                    : 'text-gray-600 dark:text-gray-400 hover:bg-gray-100 dark:hover:bg-gray-800/60'
                }`}
              >
                <Icon className="w-4 h-4" />
                {l.label}
              </Link>
            )
          })}
        </div>
      </div>
    </nav>
  )
}

function AuthGate() {
  const { authRequired, isAuthenticated } = useAuth()

  if (authRequired === null) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="text-gray-500 dark:text-gray-400">Loading...</div>
      </div>
    )
  }

  if (authRequired && !isAuthenticated) {
    return <Navigate to="/login" replace />
  }

  return (
    <div className="flex min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-200">
      <Nav />
      <div className="flex-1 min-w-0 flex flex-col min-h-screen overflow-x-hidden">
        <header className="h-14 md:h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex items-center justify-between md:justify-end px-4 md:px-8 transition-colors duration-200">
          <div className="md:hidden font-semibold text-blue-600 dark:text-blue-400 flex items-center gap-2">
            <Activity className="w-5 h-5" />
            ModelMeter
          </div>
          <div className="flex items-center gap-3">
            <div className="md:hidden">
              <LogoutButton compact />
            </div>
            <ThemeToggle />
          </div>
        </header>
        <MobileNav />
        <main className="flex-1 bg-gray-50/20 dark:bg-gray-900/20 transition-colors duration-200">
          <Suspense
            fallback={
              <div className="px-4 py-6 sm:p-8 text-gray-500 dark:text-gray-400">Loading page...</div>
            }
          >
            <Routes>
              <Route path="/" element={<Overview />} />
              <Route path="/models" element={<Models />} />
              <Route path="/models/:modelId" element={<ModelDetail />} />
              <Route path="/projects" element={<Projects />} />
              <Route path="/projects/:projectId" element={<ProjectDetail />} />
              <Route path="/live" element={<Live />} />
              <Route path="/provider-usage" element={<ProviderUsage />} />
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
      <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
        <div className="text-gray-500 dark:text-gray-400">Loading...</div>
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
                <div className="min-h-screen flex items-center justify-center bg-gray-50 dark:bg-gray-950">
                  <div className="text-gray-500 dark:text-gray-400">Loading...</div>
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
