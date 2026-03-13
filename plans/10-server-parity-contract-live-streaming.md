# Feature Plan: Server Parity, API Contract Types, and SSE Live Streaming

## Objective
Deliver three coordinated improvements in this order:
1. OpenCode-style server parity for `modelmeter serve`
2. Generated TypeScript API types from FastAPI OpenAPI schema
3. SSE-based live updates for web monitoring with polling fallback

This plan prioritizes reliability and compatibility while minimizing regressions.

## Why This Sequence
- Server behavior (auth/CORS/docs routes) must be stable before contract generation.
- Generated types should reflect the finalized API behavior.
- SSE live transport should be built on the typed contract and stable server runtime.

## Scope

### In Scope
- `modelmeter serve` parity features: `--cors`, env-based basic auth, `/doc` alias
- OpenAPI-driven TS type generation for web client consumption
- New SSE endpoint for live snapshots and frontend EventSource integration
- Tests and docs updates for all three changes

### Out of Scope
- Multi-user authz or role systems
- Websocket migration
- Hosted deployment architecture changes
- New analytics metrics unrelated to live transport

## Workstreams

### Workstream A: OpenCode-Style Server Parity (Priority 1)

#### Deliverables
- CLI:
  - `modelmeter serve --cors <origin>` (repeatable)
  - Existing `--host` and `--port` retained
- Runtime auth (optional):
  - `MODELMETER_SERVER_PASSWORD` enables HTTP Basic auth
  - `MODELMETER_SERVER_USERNAME` optional override (default `modelmeter`)
- Docs discoverability:
  - `/doc` alias (alongside `/docs` and `/openapi.json`)
- Health endpoint policy:
  - `/health` remains public for probes
  - All other routes require auth when enabled

#### Affected Areas
- `src/modelmeter/cli/main.py`
- `src/modelmeter/api/app.py`
- `src/modelmeter/config/settings.py` (if new fields are centralized)
- `README.md`

#### Acceptance Criteria
- Running `modelmeter serve --cors http://localhost:5173` allows that origin.
- Multiple `--cors` flags are honored.
- With no auth env vars set, current behavior is unchanged.
- With auth enabled, unauthenticated requests get `401` and valid Basic auth gets `200`.
- `/health` is reachable without auth.
- `/doc` is available.

#### Test Requirements
- API tests for auth on/off behavior and `/doc`.
- CLI help test showing `--cors`.

---

### Workstream B: OpenAPI Contract -> Generated TypeScript Types (Priority 3)

#### Deliverables
- Generated TS types under a dedicated folder (e.g. `web/src/generated/`).
- Thin typed API client wrapper consuming generated request/response types.
- Replace manual interfaces where contract overlap exists.
- Scripted regeneration command and CI drift check.

#### Affected Areas
- `web/package.json`
- `web/src/lib/api.ts`
- `web/src/types.ts` (reduce/retire duplicated contracts)
- `.gitlab-ci.yml`
- `README.md` / developer docs

#### Acceptance Criteria
- Web app compiles using generated API types.
- No manual duplicate response contracts for migrated endpoints.
- CI fails when generated files are stale relative to current OpenAPI schema.

#### Test Requirements
- `npm run --prefix web build` passes after migration.
- Existing frontend and backend tests continue to pass.

---

### Workstream C: SSE Live Updates with Fallback (Priority 4)

#### Deliverables
- Backend SSE endpoint (e.g. `/api/live/events`) streaming live snapshot updates.
- Frontend Live page uses EventSource for real-time updates.
- Automatic fallback to polling if SSE fails/unavailable.
- Connection-state UI handling (connected/reconnecting/fallback).

#### Affected Areas
- `src/modelmeter/api/app.py`
- `src/modelmeter/core/live.py` (reuse existing snapshot service)
- `web/src/pages/Live.tsx`
- `web/src/lib/api.ts` (optional helper utilities)

#### Acceptance Criteria
- Live page updates without periodic query polling when SSE is available.
- SSE stream respects auth behavior from Workstream A.
- On stream failure, UI falls back to polling and remains functional.

#### Test Requirements
- API test validating SSE endpoint response type and event framing basics.
- Frontend test (or integration check) for fallback behavior.

## Milestones

### Milestone 1: Server Parity Complete
- Implement Workstream A
- Run: `uv run pytest -q`
- Update README serve usage

### Milestone 2: Contract Generation Integrated
- Implement Workstream B
- Run:
  - `npm run --prefix web build`
  - `uv run pytest -q`
- Ensure CI includes type-generation drift check

### Milestone 3: SSE Live Delivered
- Implement Workstream C
- Run:
  - `npm run --prefix web build`
  - `uv run pytest -q`
- Verify Live page SSE + fallback behavior manually

## Rollback / Safety Strategy
- Keep polling path in Live page until SSE is verified in CI.
- Keep `/api/live/snapshot` endpoint unchanged as stable fallback contract.
- Introduce auth only when env var is present to avoid breaking local defaults.

## Definition of Done
- All three workstreams completed with tests/docs updated.
- `uv run pytest -q` passes.
- `npm run --prefix web build` passes.
- `modelmeter serve` supports OpenCode-style ergonomics for local server usage.
