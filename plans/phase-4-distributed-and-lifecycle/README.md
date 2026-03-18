# Phase 4: Distributed Analytics and Lifecycle Automation

## Objective
Extend ModelMeter beyond single-machine usage with federated analytics, provider-level insights, and a safe update workflow.

## Why This Phase Exists
- Users increasingly work across multiple machines (local laptop, workstation, remote host).
- Provider-level reporting is needed for spend strategy and model governance.
- Release adoption improves when users can discover and apply updates from CLI.

## Included Plans
- [x] `16-federation-core.md` ✅ Completed 2026-03-18 (PRs #1, #15)
- [x] `17-provider-analytics.md` ✅ Completed 2026-03-16 (PR #4)
- [x] `18-auto-update-and-release-awareness.md` ✅ Completed 2026-03-15 (PRs #3, #6)
- [x] `19-dashboard-source-management-and-filtering.md` ✅ Completed 2026-03-18 (PRs #1, #15)
- [ ] `20-source-status-banner-and-loading-states.md` 📝 Plan created 2026-03-18
- [ ] `21-provider-detection-from-providerid-field.md` 📝 Plan created 2026-03-18
- [x] `TRACKING.md` (execution owner/date/status tracker)

## Dependency Map
- `16-federation-core` depends on the analytics + API + CLI contract foundations from plans `03`, `04`, `06`, and `10`.
- `17-provider-analytics` depends on shared analytics contracts from `03`/`06` and federated execution from `16`.
- `18-auto-update-and-release-awareness` depends on release artifact and version policy from `14` and `15`.
- `19-dashboard-source-management-and-filtering` depends on federated source scoping from `16` and frontend shell patterns from `07` and `11`.

## Execution Order
1. `16-federation-core`
2. `17-provider-analytics`
3. `18-auto-update-and-release-awareness`
4. `19-dashboard-source-management-and-filtering`

## Phase Exit Criteria
- ✅ Multi-machine source federation works for CLI/API/Web with graceful partial failure handling.
- ✅ Provider-level totals are available and reconcile with model totals for equivalent scope/window.
- ✅ Users can check and apply updates from CLI with explicit, non-forced actions.
- ✅ Users can manage sources in the dashboard and clearly see active scope plus project-level source attribution.

## Status: Core Phase Complete (Plans 16-19) ✅

All foundational Phase 4 plans (16-19) are implemented and merged. Plans 20-21 extend the federation experience with additional UX polish and data accuracy fixes:
- **Plan 20**: Source status banners for better visual feedback during federation
- **Plan 21**: Fix provider detection bug (~20% of messages misattributed)
