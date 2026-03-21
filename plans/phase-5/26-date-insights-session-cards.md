# 26. Session Cards in Date Insights

**Status:** Completed
**Priority:** Medium
**Dependencies:** Plan 22 (Date Insights page foundation)
**PR:** #49

## Problem Statement

Date Insights currently shows Providers and Projects tabs, but sessions for the selected date are not visible as a dedicated view. Users want to understand which sessions were active on a given day, which models they used, and how much each session cost.

## Goals

1. Add a third **Sessions tab** to the Date Insights page.
2. Show per-session card layout for the selected date.
3. Each session card shows: session ID, project name, models used, tokens, and cost.
4. Keep consistent card styling with existing Providers/Projects tabs.

## Backend Changes

### New Endpoint or Extend DateInsightsResponse

The existing `GET /api/date-insights` endpoint should include session-level data. Options:

**Option A — Extend existing response:**
Add `sessions: list[SessionUsage]` to `DateInsightsResponse`, where `SessionUsage` is a slim schema with session-level aggregates for the selected day.

**Option B — New endpoint:**
Add `GET /api/date-insights/sessions` that returns session rows for the date with per-model breakdown.

**Recommendation:** Option A — include in existing response since session data complements the same date context. Keep it opt-in via query param (e.g., `?include=sessions`) to avoid breaking existing callers.

### SessionUsage Schema

```python
class SessionUsage(BaseModel):
    """Per-session usage for a single day."""
    session_id: str
    project_id: str | None = None
    project_name: str | None = None
    models: list[SessionModelUsage]  # per-model breakdown within session
    total_tokens: int
    total_interactions: int
    cost_usd: float | None = None
    has_pricing: bool = False
    started_at: str | None = None  # ISO timestamp

class SessionModelUsage(BaseModel):
    model_id: str
    provider: str | None = None
    usage: TokenUsage
    total_interactions: int = 0
    cost_usd: float | None = None
    has_pricing: bool = False
```

### SQL Changes

- `fetch_session_usage_for_day()` — group messages by session, compute per-model tokens, derive cost.
- Include `started_at` from earliest message in session.

## Frontend Changes

### Tab Switcher

Add a third tab button to the existing segmented control:

```tsx
<button type="button" onClick={() => setActiveTab('sessions')}>
  <Activity className="w-3.5 h-3.5" />
  Sessions
  <span className="...">{sessionCount}</span>
</button>
```

### Sessions Tab State

```tsx
const [activeTab, setActiveTab] = useState<Tab>('providers' | 'projects' | 'sessions')
```

### Session Cards Layout

Grid of cards (`grid-cols-1 lg:grid-cols-2`), each card:

**Card header:**
- Session ID (truncated, with copy button or title tooltip)
- Project name badge
- Started-at timestamp

**Model breakdown:** (collapsed by default if > 3 models, expandable)
- Provider badge (colored) + model name
- Tokens + cost per model

**Session totals bar:**
- Total tokens
- Total cost
- Total interactions

**Sorting:** by total_tokens descending (most active session first).

**Styling:** match existing card design — `ds-surface`, `borderTop` accent from dominant provider color, `hover:-translate-y-0.5` lift, `animate-slide-up`.

### Empty State

"No sessions recorded on this date." with Activity icon.

## Contract and Types

- Add `SessionUsage` and `SessionModelUsage` to `models.py`.
- Add `sessions: list[SessionUsage]` to `DateInsightsResponse`.
- Regenerate OpenAPI + TypeScript types.

## Acceptance Criteria

- [ ] Sessions tab appears in Date Insights tab switcher.
- [ ] Session cards show session ID, project, models used, tokens, cost.
- [ ] Session model rows are expandable with "Show X more" toggle.
- [ ] Cards are sorted by total tokens descending.
- [ ] Empty state shown when no sessions for the date.
- [ ] Card styling is consistent with Providers and Projects tabs.
- [ ] Frontend tests updated.
- [ ] Backend API tests updated.

## Validation

- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
- `uv run pytest tests/test_api.py`
- `make gen-types` and `npm run --prefix web check:types`

## Notes

- If session count is very large for a date, consider pagination or "top 20 by tokens" default with expand.
- `started_at` should use local timezone when available from message data.
