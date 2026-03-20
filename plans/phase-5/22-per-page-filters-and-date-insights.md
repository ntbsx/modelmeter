# 22. Per-Page Filters and Date Insights

**Status:** Planned  
**Priority:** High  
**Dependencies:** None

## Problem Statement

The time filter is currently controlled globally, which makes cross-page navigation carry state in ways that are not always intentional. Users also need a dedicated way to inspect one exact date and understand spend and tokens by model, provider, and project.

## Goals

1. Move time filtering from app-global header controls to page-level controls.
2. Keep source scope as the only global data scope control.
3. Add a dedicated date insights page for one-day breakdown analysis.
4. Keep URL-driven state for shareable and restorable views.
5. Add a clear, non-blocking auth warning when running server/web without password protection.

## Implementation Plan

### 1) Remove Global Time Filter

- Remove global `DaysFilterPicker` placement in `web/src/App.tsx`.
- Keep `SourceScopePicker` global.
- Keep existing auth/theme/header shell behavior unchanged.

### 2) Add Page-Local Time Controls

- Introduce a reusable page-local time filter component/hook pair.
- Apply to:
  - Overview
  - Models
  - Providers
  - Projects
  - Model detail (if endpoint semantics remain day-window based)
- Persist page-local filter in route query params.

### 3) Add Date Insights Page

- Add a new route/page for date-specific analytics drill-down.
- Include:
  - date picker
  - daily totals (tokens, cost, interactions)
  - breakdown sections by model/provider/project
- Prefer a dedicated backend contract when existing `days` window endpoints are not precise enough for arbitrary date selection.

### 4) Contract and Data Notes

- If new API endpoint is required, include source metadata fields for consistency:
  - `source_scope`
  - `sources_considered`
  - `sources_succeeded`
  - `sources_failed`
- Regenerate OpenAPI/types only when contract changes.

### 5) Auth Safety Warning (Web + Terminal)

- Web: show a small warning banner when `/health` reports `auth_required: false`.
- Terminal: print a startup warning when running server mode without `MODELMETER_SERVER_PASSWORD`.
- Behavior: warning is informational only (does not block startup or page usage).
- Message intent: clearly state the server is running without authentication.

## Acceptance Criteria

- [ ] App header has no global days/date control.
- [ ] Source scope remains global and unchanged.
- [ ] Each target page owns its own time filter UI and request params.
- [ ] New date insights page can inspect one exact date.
- [ ] Date insights shows model/provider/project daily breakdown with spend and tokens.
- [ ] URL state is preserved per-page and deep-linkable.
- [ ] Web shows a visible warning when auth is disabled.
- [ ] Terminal startup shows a warning when running server mode without password.
- [ ] No auth warning is shown when password auth is enabled.

## Validation

- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
- `uv run pytest tests/test_api.py`
- `make gen-types` and `npm run --prefix web check:types` (if API changed)
