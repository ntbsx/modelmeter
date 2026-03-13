import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Routes, Route, Link, useLocation } from 'react-router-dom'
import { Activity, BarChart2, FolderGit2, Cpu } from 'lucide-react'
import Overview from './pages/Overview'
import Models from './pages/Models'
import Projects from './pages/Projects'
import Live from './pages/Live'
import { ThemeProvider } from './components/ThemeProvider'
import { ThemeToggle } from './components/ThemeToggle'

const queryClient = new QueryClient()

function Nav() {
  const location = useLocation()
  
  const links = [
    { to: '/', icon: BarChart2, label: 'Overview' },
    { to: '/models', icon: Cpu, label: 'Models' },
    { to: '/projects', icon: FolderGit2, label: 'Projects' },
    { to: '/live', icon: Activity, label: 'Live' },
  ]

  return (
    <nav className="w-64 border-r border-gray-200 dark:border-gray-800 min-h-screen bg-gray-50/50 dark:bg-gray-900/50 p-4 flex flex-col">
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
    </nav>
  )
}

function App() {
  return (
    <ThemeProvider defaultTheme="system" storageKey="modelmeter-theme">
      <QueryClientProvider client={queryClient}>
        <BrowserRouter>
          <div className="flex min-h-screen bg-white dark:bg-gray-950 text-gray-900 dark:text-gray-100 transition-colors duration-200">
            <Nav />
            <div className="flex-1 flex flex-col min-h-screen">
              <header className="h-16 border-b border-gray-200 dark:border-gray-800 bg-white dark:bg-gray-950 flex items-center justify-end px-8 transition-colors duration-200">
                <ThemeToggle />
              </header>
              <main className="flex-1 bg-gray-50/20 dark:bg-gray-900/20 transition-colors duration-200">
                <Routes>
                  <Route path="/" element={<Overview />} />
                  <Route path="/models" element={<Models />} />
                  <Route path="/projects" element={<Projects />} />
                  <Route path="/live" element={<Live />} />
                </Routes>
              </main>
            </div>
          </div>
        </BrowserRouter>
      </QueryClientProvider>
    </ThemeProvider>
  )
}

export default App
