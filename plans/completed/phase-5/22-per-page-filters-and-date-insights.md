# 22. Per-Page Filters and Date Insights

**Status:** Completed  
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

## What Was Built

### Per-Page Filters

- Removed global `DaysFilterPicker` from `web/src/App.tsx`.
- `DaysFilterPicker` now lives in individual page local controls.
- Source scope remains global and unchanged.

### Date Insights Page

- New route `/date-insights` with a calendar date picker.
- Dedicated backend endpoint `GET /api/date-insights` with `token_source=auto` logic (prefers `part`/`steps` table over `message` table).
- Data consistency fixed: both Date Insights and Overview now use the same auto-preference logic.
- KPI cards: tokens, interactions, sessions, cost.
- **Tabbed interface**: Providers tab and Projects tab, using a segmented control with count badges.
- **Card-based layout** (not tables): each provider is a card, each project is a card.
- **Provider cards**: provider name in colored badge header, model rows inside (expandable), totals bar at bottom (tokens, cost, requests).
- **Project cards**: project name + path, per-model breakdown with provider badges (expandable), totals bar.
- Expandable rows: "Show X more" / "Show less" toggle with animated chevron.
- Cards sorted by cost descending.
- Cards have hover lift effect and border-top accent color per provider.
- `project_model_rows` data exposed in `DateInsightsResponse` as `project_models: list[ProjectModelUsage]`.
- `provider_id` extraction fixed in `fetch_project_model_usage_for_day` SQL.

### Auth Safety Warning

- Web: non-blocking warning in `App.tsx` when `/health` reports `auth_required: false`.
- Terminal: startup warning in `main.py` when running server mode without `MODELMETER_SERVER_PASSWORD`.

## Implementation Plan

### 1) Remove Global Time Filter

- ✅ Remove global `DaysFilterPicker` placement in `web/src/App.tsx`.
- ✅ Keep `SourceScopePicker` global.
- ✅ Keep existing auth/theme/header shell behavior unchanged.

### 2) Add Page-Local Time Controls

- ✅ Introduced a reusable page-local time filter component/hook pair.
- ✅ Applied to: Overview, Models, Providers, Projects, Date Insights.
- ✅ Persist page-local filter in route query params.

### 3) Add Date Insights Page

- ✅ Added new route/page for date-specific analytics drill-down.
- ✅ Includes: date picker, daily totals (tokens, cost, interactions), breakdown by model/provider/project.
- ✅ Backend endpoint with source metadata fields: `source_scope`, `sources_considered`, `sources_succeeded`, `sources_failed`.

### 4) Contract and Data Notes

- ✅ New API endpoint with source metadata fields for consistency.
- ✅ `ProjectModelUsage` schema added for per-model breakdown per project.
- ✅ OpenAPI/types regenerated.

### 5) Auth Safety Warning (Web + Terminal)

- ✅ Web: shows a small warning banner when `/health` reports `auth_required: false`.
- ✅ Terminal: prints a startup warning when running server mode without `MODELMETER_SERVER_PASSWORD`.
- ✅ Warning is informational only (does not block startup or page usage).

## Future Work (see Plan 26)

- Add **Sessions tab** to Date Insights page — show per-session breakdown for the selected date with card layout.

## Acceptance Criteria

- [x] App header has no global days/date control.
- [x] Source scope remains global and unchanged.
- [x] Each target page owns its own time filter UI and request params.
- [x] New date insights page can inspect one exact date.
- [x] Date insights shows model/provider/project daily breakdown with spend and tokens.
- [x] URL state is preserved per-page and deep-linkable.
- [x] Web shows a visible warning when auth is disabled.
- [x] Terminal startup shows a warning when running server mode without password.
- [x] No auth warning is shown when password auth is enabled.

## Validation

- `npm run --prefix web test -- --run` — 105 tests pass
- `npm run --prefix web build` — builds cleanly
- `uv run pytest tests/test_api.py` — 37 tests pass
- `make gen-types` — OpenAPI + TS types regenerated

## Key Files

**Backend:**
- `src/modelmeter/core/models.py` — `DateInsightsResponse`, `ProjectModelUsage`
- `src/modelmeter/core/analytics.py` — `get_date_insights()` with token_source auto logic
- `src/modelmeter/data/sqlite_usage_repository.py` — `fetch_summary_for_day_steps()`, `fetch_project_model_usage_for_day` with provider_id
- `src/modelmeter/api/app.py` — `GET /api/date-insights` endpoint

**Frontend:**
- `web/src/pages/DateInsights.tsx` — tabbed card layout (Providers + Projects)
- `web/src/components/DatePicker.tsx` — calendar grid date picker
- `web/src/hooks/useDaysFilter.ts` — page-local days filter hook
- `web/src/components/DaysFilterPicker.tsx` — page-local days picker component
