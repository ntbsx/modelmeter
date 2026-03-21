# Phase 5: Analytics UX and Exploration

## Objective

Improve analytics exploration UX so users can answer daily spend questions faster, with cleaner page-level flows and less flat table-heavy views.

## Scope Summary

Phase 5 covers:
- Per-page date/time filters (source scope stays global)
- A date-specific spend breakdown page
- Card-first list views with infinite scroll on key pages
- Chart support on models/providers/projects pages
- Multi-session live view on local or server (self) data with clearer behavior
- Sources page visual redesign to card layout
- Non-blocking auth safety warning in web and terminal when server runs without password

## Plan Set

1. `22-per-page-filters-and-date-insights.md` ✅
2. `23-card-layout-infinite-scroll-and-charts.md` ✅
3. `24-live-multi-session-and-scope-simplification.md` ✅
4. `25-sources-page-card-redesign.md` ✅
5. `26-date-insights-session-cards.md` ✅

## Execution Order

- `22` ✅ — completed, foundation for date drill-down UX (Providers + Projects tabs, card layout)
- `23` and `24` — in parallel after `22`
- `25` ✅ — Sources page card redesign completed
- `26` ✅ — Sessions tab for Date Insights completed

## Phase Exit Criteria

- [x] No global days/date filter in app shell; each page owns its own filter UX
- [x] New date insights page supports one-day spend and token breakdowns (Providers + Projects tabs, card layout)
- [x] Models, Providers, and Projects pages use cards + lazy loading + charts
- [x] Live page supports viewing multiple local/server (self) live session panels in one screen
- [x] Sources page listing uses cards instead of table rows
- [x] Web and terminal show a clear warning when server auth is disabled
- [x] Frontend tests updated for changed interactions and layout
- [x] Backend/API tests updated for new date insights contract

## Validation Baseline

- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
- `uv run pytest tests/test_api.py tests/test_federation.py tests/test_sources.py`
- `make gen-types` (if API schema changes)
- `npm run --prefix web check:types` (if API schema changes)
