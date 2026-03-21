# 24. Live Multi-Session and Scope Simplification

**Status:** Complete
**Priority:** High
**Dependencies:** 22-per-page-filters-and-date-insights.md

## Problem Statement

The current live page focuses on a single live session view. Users want to monitor multiple live sessions at once on local or server (self) data, and source selector interactions on this page are still confusing.

## Goals

1. Allow viewing multiple live session panels in one screen.
2. Remove ineffective live-only source selector behavior from the live flow.
3. Keep global source scope model consistent across the app while making Live behavior explicit.
4. Preserve robust fallback behavior (SSE to polling) per live panel.

## Implementation Plan

### 1) Live Panel Model

- Introduce a panel list where each panel maps to one live session context on local or server (self) data.
- Allow add/remove panel interactions.
- Persist selected sessions in local storage.

### 2) Data Strategy

- For each panel, run independent live connection state:
  - connecting / streaming / polling / paused
- Keep fallback logic per panel.
- Avoid unnecessary reconnect storms when adding/removing panels.

### 3) Scope UX Simplification

- Remove confusing source selector affordance from Live-specific UX.
- Replace with explicit session selection controls within the page.
- Keep the rest of app scope behavior unchanged.

### 4) Observability and Limits

- Add clear status chips per panel.
- Include safe max panel count to limit browser/network load.

## Acceptance Criteria

- [ ] Users can view multiple local/server (self) live session panels at once.
- [ ] Users can remove/add panels without page reload.
- [ ] Live page no longer implies ineffective source selector behavior.
- [ ] Each panel clearly indicates streaming/polling/paused state.
- [ ] No regressions in existing live fallback behavior.

## Validation

- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
- `uv run pytest tests/test_api.py tests/test_federation.py`
