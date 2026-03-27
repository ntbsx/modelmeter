import { Badge } from './ui'

const AGENT_LABELS: Record<string, string> = {
  opencode: 'OpenCode',
  claudecode: 'Claude Code',
}

const AGENT_VARIANTS: Record<string, 'default' | 'primary'> = {
  opencode: 'primary',
  claudecode: 'default',
}

type AgentBadgeProps = {
  agent: string | null | undefined
}

export function AgentBadge({ agent }: AgentBadgeProps) {
  if (!agent) return null

  const label = AGENT_LABELS[agent] ?? agent
  const variant = AGENT_VARIANTS[agent] ?? 'default'

  return <Badge variant={variant}>{label}</Badge>
}
