# Feature Plan: Federation Core (Multi-Machine)

## Objective
Enable pull-based multi-machine analytics by federating results from local SQLite and remote ModelMeter HTTP sources.

## Why This Matters
- Current analytics are single-source by default.
- Teams and power users commonly split work across several devices.
- Federation enables unified reporting without introducing write-path complexity.

## Scope

### In Scope
- Source registry with validated source definitions.
- Source types:
  - `sqlite` (local path or mounted path)
  - `http` (remote ModelMeter API)
- Federated fan-out/fan-in for summary, daily, models, projects, project detail, and live snapshot.
- Source scoping (`local`, `all`, `source:<id>`).
- Partial-failure handling with per-source status metadata.

### Out of Scope
- Push/event replication between machines.
- Multi-tenant hosted auth model.
- Warehouse-style precomputed aggregates.

## Workstreams

### Workstream A: Source Contracts and Registry (Priority 1)

#### Deliverables
- Add source models and validators in core contracts.
- Add registry load/save utility (default config path under user config dir).
- Add source health model for diagnostics and API response metadata.

#### Acceptance Criteria
- Invalid source configs fail fast with actionable errors.
- Empty registry preserves current single-source behavior.

#### Validation
- Unit tests for source schema, parsing, and persistence.

---

### Workstream B: Federated Analytics Execution (Priority 2)

#### Deliverables
- Add federated analytics service that executes source queries in parallel.
- Implement deterministic merge logic for totals and grouped rows.
- Namespace collision-prone row IDs (for example session IDs as `<source_id>:<session_id>`).

#### Acceptance Criteria
- Aggregated totals equal the sum of successful source responses.
- One failing source does not fail the whole response when at least one source succeeds.

#### Validation
- Integration tests with multiple sqlite fixtures.
- Integration tests with mixed sqlite/http and forced source failure.

---

### Workstream C: API and CLI Surface (Priority 3)

#### Deliverables
- Add source management CLI commands:
  - `modelmeter sources list`
  - `modelmeter sources add-sqlite`
  - `modelmeter sources add-http`
  - `modelmeter sources remove`
  - `modelmeter sources check`
- Add source-scoped analytics access in API query params.
- Add API endpoint for source health/status.

#### Acceptance Criteria
- Scope semantics are consistent between CLI and API.
- Source diagnostics expose reachable and failed sources clearly.

#### Validation
- CLI tests for source command behavior.
- API tests for scope handling and source metadata.

---

### Workstream D: Web Integration and Reliability (Priority 4)

#### Deliverables
- Add source scope controls in Overview/Models/Projects/Live pages.
- Add frontend handling for partial-source degradation notices.
- Ensure UI query behavior remains stable for mobile/desktop layouts.

#### Acceptance Criteria
- Users can switch source scope without route breaks.
- Degraded states are visible without blocking all analytics views.

#### Validation
- Frontend tests for source filter + query wiring.
- Manual responsive checks at key breakpoints.

## Milestones

### Milestone 1: Source Registry Ready
- Workstream A complete.

### Milestone 2: Federated Fan-In Operational
- Workstream B complete.

### Milestone 3: Product Surface Integration
- Workstream C and D complete.

## Definition of Done
- Federation works across `sqlite` and `http` sources.
- Scope controls are available in CLI/API/Web.
- Partial failures are visible and non-catastrophic.
- Single-source workflows remain backward compatible.

## Completion Checklist
- [ ] Workstream A complete
- [ ] Workstream B complete
- [ ] Workstream C complete
- [ ] Workstream D complete
