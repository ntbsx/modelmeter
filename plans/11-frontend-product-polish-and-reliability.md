# Feature Plan: Frontend Product Polish and Reliability

## Objective
Improve frontend quality and usability after core feature delivery by focusing on:
1. Consistent loading/error/empty UX
2. Better analytics visualization and controls
3. Live page resilience and responsiveness
4. Frontend quality gates in CI and release workflow

## Why Now
- Core product functionality is complete and stable.
- Remaining gaps are mostly UX consistency, frontend lint debt, and operational polish.
- This work reduces regressions and increases confidence before broader adoption.

## Scope

### In Scope
- Frontend lint cleanup to reach green `npm run --prefix web lint`
- Unified UX states across pages (loading/error/empty)
- Overview chart upgrades (range selector and data controls)
- Project detail page usability enhancements (sort/filter/search)
- Live page reliability UX (reconnect state, status clarity)
- Frontend CI guardrails (explicit lint/build/type checks)
- Release checklist/docs polish for frontend validation

### Out of Scope
- New backend analytics metrics not required by current UX
- Auth/permissions or multi-user hosted concerns
- Full design system migration
- i18n/localization

## Workstreams

### Workstream A: Frontend Quality Baseline (Priority 1)

#### Deliverables
- Resolve existing frontend lint errors and enforce clean baseline.
- Confirm strict TypeScript build remains green.
- Add/verify CI job that explicitly runs frontend lint.

#### Acceptance Criteria
- `npm run --prefix web lint` passes.
- `npm run --prefix web build` passes.
- CI fails on frontend lint regressions.

#### Validation
- `npm run --prefix web lint`
- `npm run --prefix web build`

---

### Workstream B: UX State Consistency (Priority 2)

#### Deliverables
- Reusable components for:
  - Loading skeletons (already introduced)
  - Error state panel
  - Empty state panel
- Apply consistently to:
  - Overview
  - Models
  - Projects
  - Project Detail
  - Live

#### Acceptance Criteria
- No plain text-only loading/error screens on primary pages.
- Spacing and container widths are consistent across pages and breakpoints.
- Mobile and desktop visual consistency validated manually.

#### Validation
- Manual checks at common widths: 390px, 768px, 1024px, 1440px.
- `npm run --prefix web build`

---

### Workstream C: Overview Analytics Experience (Priority 3)

#### Deliverables
- Keep composed trend chart (tokens/sessions/cost).
- Add range selector (7/30/90 days).
- Add optional series toggles:
  - tokens
  - sessions
  - cost
- Improve tooltip readability and accessibility labels.

#### Acceptance Criteria
- Range switch updates cards + chart coherently.
- Chart remains readable in dark/light themes.
- No layout overflow at mobile widths.

#### Validation
- Manual UX checks + `npm run --prefix web build`.

---

### Workstream D: Project Detail Usability (Priority 4)

#### Deliverables
- Session table controls:
  - Search by session title/id
  - Sort by last updated (default), tokens, cost
- Keep server ordering default as last-updated desc.
- Preserve responsive behavior for long IDs/paths.

#### Acceptance Criteria
- User can quickly locate a session in medium/large datasets.
- Default sort remains last updated descending.
- No horizontal page overflow on mobile.

#### Validation
- Manual behavior verification on Project Detail route.
- Existing API + frontend build checks pass.

---

### Workstream E: Live Reliability UX (Priority 5)

#### Deliverables
- Clear transport badge states:
  - connecting
  - streaming
  - polling fallback
- Reconnect feedback (e.g., "retrying in Xs" indicator).
- Optional pause/resume updates control.

#### Acceptance Criteria
- Transport mode is obvious at all times.
- Fallback behavior is discoverable and non-disruptive.
- Live page container/layout remains consistent with app shell.

#### Validation
- Manual live stream/fallback simulation.
- `npm run --prefix web build`

---

### Workstream F: Performance and Release Guardrails (Priority 6)

#### Deliverables
- Route-level code splitting for heavier pages (e.g., Overview/Live).
- Keep bundle warnings tracked and documented.
- Add frontend section to release checklist:
  - lint
  - build
  - generated API artifacts check

#### Acceptance Criteria
- Bundle strategy documented and active.
- Release process includes explicit frontend quality gates.
- No regressions in current `make release-check` flow.

#### Validation
- `npm run --prefix web build`
- `npm run --prefix web check:types`
- `make release-check`

## Milestones

### Milestone 1: Frontend Baseline Green
- Workstream A complete
- CI updated for explicit frontend lint enforcement

### Milestone 2: UX Consistency Delivered
- Workstream B complete
- Width/container parity validated across primary pages

### Milestone 3: Analytics and Detail UX Upgrades
- Workstreams C and D complete
- Overview + Project Detail controls delivered

### Milestone 4: Live + Performance Polish
- Workstreams E and F complete
- Release workflow fully frontend-aware

## Definition of Done
- Frontend lint/build/type checks consistently pass locally and in CI.
- Primary pages have consistent loading/error/empty states.
- Overview and Project Detail interactions feel production-ready.
- Live page communicates transport/fallback clearly.
- Release checklist captures frontend quality requirements.

## Completion Checklist
- [x] Workstream A complete
- [x] Workstream B complete
- [x] Workstream C complete
- [x] Workstream D complete
- [x] Workstream E complete
- [x] Workstream F complete
