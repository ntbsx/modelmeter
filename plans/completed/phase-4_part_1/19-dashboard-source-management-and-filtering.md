# Feature Plan: Dashboard Source Management and Filtering

## Objective
Add first-class source awareness to the web product so users can manage sources from the dashboard, choose the active source scope across all analytics pages, and understand which sources contributed to project-level results.

## Why This Matters
- Multi-machine federation is hard to trust if the dashboard does not say what data is being shown.
- Source registration must be available in the web UI for non-CLI users.
- Project views are the most likely place for users to ask, "which machine did this come from?"

## Product Defaults
- Default dashboard scope: `local`
- Optional scopes:
  - `all`
  - `source:<id>`
- The active scope must always be visible in the app shell and reflected in request state.

## Scope

### In Scope
- Dashboard source CRUD for `sqlite` and `http` sources.
- Shared source scope selector for Overview, Providers, Models, Projects, Project Detail, and Live.
- Response metadata for source scope and source health/degradation.
- Project list and project detail source attribution.
- URL and query-state handling for source scope.

### Out of Scope
- Background replication between instances.
- Automatic source discovery on the local network.
- Multi-user permissions for editing sources.

## Workstreams

### Workstream A: Source-Aware Contracts and API Surface (Priority 1)

#### Deliverables
- Define a shared source scope contract for API and frontend use.
- Add source-aware query params to analytics and live endpoints.
- Add source management API endpoints for create, update, delete, and health check.
- Add response metadata fields such as:
  - `source_scope`
  - `sources_considered`
  - `sources_succeeded`
  - `sources_failed`

#### Acceptance Criteria
- Every analytics endpoint accepts the same scope semantics.
- Invalid source scope values fail fast with actionable errors.
- OpenAPI and generated frontend types stay in sync.

#### Validation
- API tests for scope parsing, source CRUD, and failure metadata.
- Contract snapshot regeneration and verification.

---

### Workstream B: Federated Dashboard Query Layer (Priority 1)

#### Deliverables
- Add a backend federation layer that can fan out analytics requests to configured sources.
- Merge summary, daily, provider, model, project, project detail, and live responses deterministically.
- Preserve partial-source failure metadata without failing the whole dashboard when at least one source succeeds.

#### Acceptance Criteria
- `local` preserves current single-source behavior.
- `all` returns merged totals across successful sources.
- `source:<id>` returns only that source's data.
- Project and session identifiers remain stable and collision-safe when merged.

#### Validation
- Integration tests with multiple sqlite fixtures.
- Integration tests with mixed sqlite/http sources and forced source failures.

---

### Workstream C: Web Source Management UX (Priority 2)

#### Deliverables
- Add a dashboard-visible source management surface.
- Support:
  - list configured sources
  - add sqlite source
  - add HTTP source
  - remove source
  - run source health checks
- Redact credentials after save while still showing whether auth is configured.

#### Acceptance Criteria
- Users can manage sources without using the CLI.
- Validation errors are visible inline and map cleanly to API failures.
- Source health status is easy to inspect before using `all` scope.

#### Validation
- Frontend tests for add/remove/check flows.
- Manual responsive checks for mobile and desktop layouts.

---

### Workstream D: Global Scope UX and Attribution (Priority 2)

#### Deliverables
- Add a persistent source scope selector in the app shell.
- Add an active scope badge/indicator on every dashboard page.
- Update all page queries to include source scope in request params and cache keys.
- Show source attribution in project list and project detail.

#### Acceptance Criteria
- Scope changes propagate consistently across all analytics views.
- The active scope survives navigation and refresh.
- Project rows show which source or sources contributed to the aggregate.
- Project detail shows project-level source badges and, when needed, session-level source attribution.

#### Validation
- Frontend tests for shared source scope state and URL sync.
- API/UI tests for project source attribution.

## API and Contract Notes
- Recommended request shape:
  - `source_scope=local`
  - `source_scope=all`
  - `source_scope=source:<id>`
- Recommended top-level response metadata on source-aware analytics endpoints:
  - `source_scope: str`
  - `sources_considered: list[str]`
  - `sources_succeeded: list[str]`
  - `sources_failed: list[SourceFailure]`
- Recommended project attribution fields:
  - `source_ids: list[str]`
  - optional `source_count: int`

## UI Notes
- Primary app-shell additions:
  - `SourceScopePicker`
  - `ActiveSourceBadge`
  - source manager entry point in nav or header
- Project table additions:
  - `Sources` column with compact badges
- Project detail additions:
  - source badges near project title
  - optional per-session source badge when merged results make origin ambiguous

## Milestones

### Milestone 1: Source-Aware API Contracts Stable
- Workstream A complete.

### Milestone 2: Federated Scope Queries Operational
- Workstream B complete.

### Milestone 3: Dashboard Source Management Shipped
- Workstream C complete.

### Milestone 4: Global Scope UX and Project Attribution Shipped
- Workstream D complete.

## Definition of Done
- Users can add and inspect sources from the dashboard.
- Every analytics page exposes and respects a shared source scope.
- The dashboard clearly indicates the active source scope.
- Project list and project detail views expose contributing sources.
- Partial-source degradation is visible without collapsing the whole dashboard.

## Completion Checklist
- [ ] Workstream A complete
- [ ] Workstream B complete
- [ ] Workstream C complete
- [ ] Workstream D complete
