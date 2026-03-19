import { useTheme } from './useTheme'

type ChartColors = {
  tokens: {
    stroke: string
    fill: string
  }
  sessions: {
    stroke: string
    fill: string
  }
  cost: {
    stroke: string
    fill: string
  }
  grid: string
  axis: string
  tooltip: {
    background: string
    border: string
    text: string
  }
}

export function useChartColors(): ChartColors {
  const { theme } = useTheme()
  const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches)

  if (isDark) {
    return {
      tokens: {
        stroke: 'var(--chart-tokens)',
        fill: 'var(--chart-tokens)',
      },
      sessions: {
        stroke: 'var(--chart-sessions)',
        fill: 'var(--chart-sessions)',
      },
      cost: {
        stroke: 'var(--chart-cost)',
        fill: 'var(--chart-cost)',
      },
      grid: '#374151',
      axis: '#9ca3af',
      tooltip: {
        background: '#1f2937',
        border: '#374151',
        text: '#f9fafb',
      },
    }
  }

  return {
    tokens: {
      stroke: 'var(--chart-tokens)',
      fill: 'var(--chart-tokens)',
    },
    sessions: {
      stroke: 'var(--chart-sessions)',
      fill: 'var(--chart-sessions)',
    },
    cost: {
      stroke: 'var(--chart-cost)',
      fill: 'var(--chart-cost)',
    },
    grid: '#f3f4f6',
    axis: '#6b7280',
    tooltip: {
      background: '#ffffff',
      border: '#e5e7eb',
      text: '#111827',
    },
  }
}
