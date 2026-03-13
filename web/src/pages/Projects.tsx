import { useQuery } from '@tanstack/react-query'
import { fetchApi } from '../lib/api'
import { formatTokens, formatUsd } from '../lib/utils'

export default function Projects() {
  const { data, isLoading } = useQuery<any>({
    queryKey: ['projects'],
    queryFn: () => fetchApi('/projects', { days: 7 })
  })

  if (isLoading) return <div className="p-8 text-gray-500 dark:text-gray-400">Loading...</div>
  if (!data) return <div className="p-8 text-red-500 dark:text-red-400">Failed to load projects.</div>

  return (
    <div className="p-8 max-w-6xl mx-auto">
      <div className="mb-8">
        <h1 className="text-2xl font-bold text-gray-900 dark:text-white">Projects</h1>
        <p className="text-gray-500 dark:text-gray-400">Usage breakdown by project workspace (last 7 days)</p>
      </div>

      <div className="bg-white dark:bg-gray-900 rounded-xl border border-gray-200 dark:border-gray-800 shadow-sm overflow-hidden transition-colors">
        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead className="bg-gray-50 dark:bg-gray-800/50 border-b border-gray-200 dark:border-gray-800 text-gray-500 dark:text-gray-400">
              <tr>
                <th className="px-6 py-4 font-medium whitespace-nowrap">Project</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Sessions</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Total Tokens</th>
                <th className="px-6 py-4 font-medium text-right whitespace-nowrap">Cost</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100 dark:divide-gray-800">
              {data.projects.map((p: any) => (
                <tr key={p.project_id} className="hover:bg-gray-50/50 dark:hover:bg-gray-800/30 transition-colors">
                  <td className="px-6 py-4">
                    <div className="font-medium text-gray-900 dark:text-gray-100 truncate max-w-sm" title={p.project_name}>
                      {p.project_name.split('/').pop() || p.project_name}
                    </div>
                    <div className="text-xs text-gray-400 dark:text-gray-500 truncate max-w-sm mt-0.5" title={p.project_path || p.project_id}>
                      {p.project_path || p.project_id}
                    </div>
                  </td>
                  <td className="px-6 py-4 text-right text-gray-600 dark:text-gray-400">{p.total_sessions}</td>
                  <td className="px-6 py-4 text-right font-mono text-gray-900 dark:text-gray-100">{formatTokens(p.usage.total_tokens)}</td>
                  <td className="px-6 py-4 text-right font-mono text-gray-900 dark:text-gray-100">{p.cost_usd ? formatUsd(p.cost_usd) : '-'}</td>
                </tr>
              ))}
              {data.projects.length === 0 && (
                <tr>
                  <td colSpan={4} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">No project usage found in this period.</td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  )
}
