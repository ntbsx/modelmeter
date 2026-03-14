# Feature Plan: Provider-Level Analytics

## Objective
Add provider-level analysis so users can understand usage and cost by provider (for example OpenAI, Anthropic) across single-source and federated scopes.

## Why This Matters
- Model-level reporting is detailed but not ideal for portfolio-level decisions.
- Provider-level rollups help with spend controls, vendor mix, and routing policy decisions.
- Federation increases the need for normalized cross-source grouping.

## Scope

### In Scope
- Provider attribution from `model_id` with safe fallback to `unknown`.
- Optional provider enrichment using pricing/metadata when available.
- New provider contracts and analytics endpoint/command.
- Provider visualization/filtering in web views.

### Out of Scope
- Contracting/billing integrations with provider accounts.
- Custom provider taxonomies per organization.

## Workstreams

### Workstream A: Provider Attribution Rules (Priority 1)

#### Deliverables
- Add provider extraction utility with deterministic rules.
- Add enrichment hook using pricing metadata when available.
- Document precedence rules (model prefix first, metadata fallback second).

#### Acceptance Criteria
- Known model IDs map to stable provider labels.
- Unknown or non-standard IDs map to `unknown` without crashing.

#### Validation
- Unit tests for provider parsing edge cases.

---

### Workstream B: Provider Contracts and Aggregations (Priority 2)

#### Deliverables
- Add `ProviderUsage` and `ProvidersResponse` contracts.
- Add provider aggregation in analytics service for scoped windows.
- Include cost, interactions, session count, and token totals per provider.

#### Acceptance Criteria
- Provider totals reconcile with model totals for equivalent filters.
- Pagination and sorting behavior remain deterministic.

#### Validation
- Analytics tests for reconciliation and ordering.

---

### Workstream C: CLI/API Exposure (Priority 3)

#### Deliverables
- Add CLI command: `modelmeter providers` (+ `--json`).
- Add API endpoint: `GET /api/providers`.
- Support scope/time filters consistent with other analytics endpoints.

#### Acceptance Criteria
- CLI and API payloads match shared contracts.
- Error behavior aligns with existing API/CLI conventions.

#### Validation
- API tests and CLI JSON output tests.

---

### Workstream D: Web Product Integration (Priority 4)

#### Deliverables
- Add provider cards/table to Overview or dedicated provider section.
- Add provider grouping/filter controls in Models view.
- Ensure mobile-friendly rendering for provider tables/charts.

#### Acceptance Criteria
- Provider analysis is discoverable in the dashboard.
- Source scope + provider filters can be combined safely.

#### Validation
- Frontend tests for provider query/UI state.
- Manual checks for layout and readability.

## Milestones

### Milestone 1: Attribution and Contracts
- Workstream A and B complete.

### Milestone 2: Product Surfaces
- Workstream C and D complete.

## Definition of Done
- Provider-level metrics are available in CLI/API/Web.
- Provider totals reconcile with model totals for same scope/window.
- Edge-case IDs are safely classified as `unknown`.

## Completion Checklist
- [ ] Workstream A complete
- [ ] Workstream B complete
- [ ] Workstream C complete
- [ ] Workstream D complete
