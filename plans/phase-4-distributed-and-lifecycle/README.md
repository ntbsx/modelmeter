# Phase 4: Distributed Analytics and Lifecycle Automation

## Objective
Extend ModelMeter beyond single-machine usage with federated analytics, provider-level insights, and a safe update workflow.

## Why This Phase Exists
- Users increasingly work across multiple machines (local laptop, workstation, remote host).
- Provider-level reporting is needed for spend strategy and model governance.
- Release adoption improves when users can discover and apply updates from CLI.

## Included Plans
- [ ] `16-federation-core.md`
- [ ] `17-provider-analytics.md`
- [ ] `18-auto-update-and-release-awareness.md`
- [ ] `19-dashboard-source-management-and-filtering.md`
- [ ] `TRACKING.md` (execution owner/date/status tracker)

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
- Multi-machine source federation works for CLI/API/Web with graceful partial failure handling.
- Provider-level totals are available and reconcile with model totals for equivalent scope/window.
- Users can check and apply updates from CLI with explicit, non-forced actions.
- Users can manage sources in the dashboard and clearly see active scope plus project-level source attribution.
