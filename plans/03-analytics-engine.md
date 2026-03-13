# Feature Plan: Analytics Engine (DONE)

## Objective
Produce accurate, reusable usage analytics for CLI and future web API.

## Scope
- Token aggregation (input/output/cache read/cache write)
- Daily, model, and project breakdowns
- Optional cost computation using model pricing data
- Time-window filtering and project scoping

## Deliverables
- Aggregators:
  - summary totals
  - daily series
  - model usage table
  - single-model deep-dive
  - project usage table
- Cost service with precedence:
  - local override
  - built-in defaults
  - optional remote fallback
- Stable output contracts for all analytics

## Key Decisions
- Keep "unknown model" bucket instead of dropping data
- Cost as optional enrichment, never hard requirement
- Preserve raw token fields in outputs for auditability

## Acceptance Criteria
- Daily totals match session-level sums
- Model totals match global totals (within unknown bucket rules)
- JSON outputs are stable and versioned
