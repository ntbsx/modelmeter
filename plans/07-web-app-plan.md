# Feature Plan: Web Application (DONE)

## Objective
Create a browser UI on top of the API with parity to CLI analytics.

## Scope
- Dashboard for summary + daily chart + top models/projects
- Model detail page
- Live monitor page
- Date/filter controls and refresh behavior

## Deliverables
- Frontend app scaffold (React + Vite or Next.js)
- Typed API client generated or handwritten from OpenAPI contracts
- Core pages:
  - Overview
  - Models
  - Model Detail
  - Projects
  - Live
- States: loading, empty, error, stale-data warning

## Key Decisions
- Prefer server contract-driven UI components
- Keep initial UI local-only, no multi-user complexity
- Focus on data clarity over visual complexity in v1

## Acceptance Criteria
- All key CLI analytics are visible in web UI
- Filters sync with URL query params
- Live page polls/syncs reliably
