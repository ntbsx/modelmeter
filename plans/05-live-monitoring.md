# Feature Plan: Live Monitoring (DONE)

## Objective
Provide near-real-time visibility into current OpenCode activity.

## Scope
- Polling-based live dashboard (configurable interval)
- Active workflow/session detection
- Rolling token and cost deltas
- Tool usage and per-model live counters (if available)

## Deliverables
- `live` command with stable refresh loop
- Snapshot service (`get_live_snapshot()`) in core
- Visual panels for activity, tokens, models, tools
- Safe behavior when no active session exists

## Key Decisions
- Polling over DB watch for portability
- Keep refresh independent from render layer
- Degrade gracefully on partial data

## Acceptance Criteria
- Live view updates without flicker regressions
- Ctrl+C exits cleanly
- Dashboard remains usable with sparse/missing fields
