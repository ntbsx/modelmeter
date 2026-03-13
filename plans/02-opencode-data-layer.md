# Feature Plan: OpenCode Data Layer (DONE)

## Objective
Read OpenCode usage safely from official storage paths and normalize schema drift.

## Scope
- Detect OpenCode storage locations:
  - `~/.local/share/opencode/opencode.db` (primary)
  - project/legacy storage fallback
- Read tables used by usage analytics (`session`, `message`, `part`, `project`)
- Parse message JSON shape variants defensively

## Deliverables
- Storage detector with override support (`--db-path`, env vars)
- SQLite read-only repository layer
- Legacy loader adapter (if SQLite unavailable)
- Schema capability checks (`doctor` diagnostics payload)

## Key Decisions
- Open DB in read-only mode whenever possible
- Never mutate OpenCode DB
- Add compatibility gates for missing columns/tables

## Acceptance Criteria
- Can load sessions on macOS and Linux defaults
- Graceful error messages for permission/path/schema issues
- Fallback path works when SQLite absent
