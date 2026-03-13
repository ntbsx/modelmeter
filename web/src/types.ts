export interface TokenUsage {
  input_tokens: number
  output_tokens: number
  cache_read_tokens: number
  cache_write_tokens: number
  total_tokens: number
}

export interface SummaryResponse {
  usage: TokenUsage
  total_sessions: number
  window_days: number | null
  cost_usd: number | null
  pricing_source: string | null
}

export interface DailyUsage {
  day: string
  usage: TokenUsage
  total_sessions: number
  cost_usd: number | null
}

export interface DailyResponse {
  window_days: number | null
  totals: TokenUsage
  total_sessions: number
  total_cost_usd: number | null
  pricing_source: string | null
  daily: DailyUsage[]
}

export interface ModelUsage {
  model_id: string
  usage: TokenUsage
  total_sessions: number
  total_interactions: number
  cost_usd: number | null
  has_pricing: boolean
}

export interface ModelsResponse {
  window_days: number | null
  totals: TokenUsage
  total_sessions: number
  total_cost_usd: number | null
  pricing_source: string | null
  priced_models: number
  unpriced_models: number
  models: ModelUsage[]
}
