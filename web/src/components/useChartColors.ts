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
    grid: 'var(--border-default)',
    axis: 'var(--text-tertiary)',
    tooltip: {
      background: 'var(--surface-primary)',
      border: 'var(--border-default)',
      text: 'var(--text-primary)',
    },
  }
}
