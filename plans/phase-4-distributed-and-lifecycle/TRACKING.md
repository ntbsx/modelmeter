# Phase 4 Tracking Checklist

## Usage
- Update one row per workstream as implementation progresses.
- Keep `Status` to one of: `not_started`, `in_progress`, `blocked`, `done`.
- Use ISO dates (`YYYY-MM-DD`) for `Start Date` and `Target Date`.

## Workstream Tracker

| ID | Plan | Workstream | Owner | Start Date | Target Date | Status | Notes / PR |
|---|---|---|---|---|---|---|---|
| 16A | `16-federation-core.md` | Source Contracts and Registry | ntbsx | 2026-03-17 | 2026-03-17 | done | PR #1 (9a45d4f) |
| 16B | `16-federation-core.md` | Federated Analytics Execution | ntbsx | 2026-03-17 | 2026-03-18 | done | PR #15 (af823dc) |
| 16C | `16-federation-core.md` | API and CLI Surface | ntbsx | 2026-03-17 | 2026-03-18 | done | PR #1, #15 |
| 16D | `16-federation-core.md` | Web Integration and Reliability | ntbsx | 2026-03-18 | 2026-03-18 | done | PR #15 (af823dc) |
| 17A | `17-provider-analytics.md` | Provider Attribution Rules | ntbsx | 2026-03-15 | 2026-03-16 | done | PR #4 (cf19b9d) |
| 17B | `17-provider-analytics.md` | Provider Contracts and Aggregations | ntbsx | 2026-03-15 | 2026-03-16 | done | PR #4 (cf19b9d) |
| 17C | `17-provider-analytics.md` | CLI/API Exposure | ntbsx | 2026-03-15 | 2026-03-16 | done | PR #4 (cf19b9d) |
| 17D | `17-provider-analytics.md` | Web Product Integration | ntbsx | 2026-03-15 | 2026-03-16 | done | PR #4 (cf19b9d) |
| 18A | `18-auto-update-and-release-awareness.md` | Updater Core and Version Semantics | ntbsx | 2026-03-14 | 2026-03-15 | done | PR #3 (c35064b) |
| 18B | `18-auto-update-and-release-awareness.md` | CLI Update Commands | ntbsx | 2026-03-14 | 2026-03-15 | done | PR #3 (c35064b) |
| 18C | `18-auto-update-and-release-awareness.md` | Passive Release Awareness | ntbsx | 2026-03-14 | 2026-03-15 | done | PR #6 (d890d52) |
| 18D | `18-auto-update-and-release-awareness.md` | Docs and Release Runbook Alignment | ntbsx | 2026-03-14 | 2026-03-15 | done | PR #3 (c35064b) |
| 19A | `19-dashboard-source-management-and-filtering.md` | Source-Aware Contracts and API Surface | ntbsx | 2026-03-17 | 2026-03-18 | done | PR #1, #15 |
| 19B | `19-dashboard-source-management-and-filtering.md` | Federated Dashboard Query Layer | ntbsx | 2026-03-17 | 2026-03-18 | done | PR #15 (af823dc) |
| 19C | `19-dashboard-source-management-and-filtering.md` | Web Source Management UX | ntbsx | 2026-03-17 | 2026-03-18 | done | PR #15 (af823dc) |
| 19D | `19-dashboard-source-management-and-filtering.md` | Global Scope UX and Attribution | ntbsx | 2026-03-17 | 2026-03-18 | done | PR #15 (af823dc) |
| 20A | `20-source-status-banner-and-loading-states.md` | Banner Component and Contracts | TBD | TBD | TBD | not_started | Plan created 2026-03-18 |
| 20B | `20-source-status-banner-and-loading-states.md` | Integration Across Data Pages | TBD | TBD | TBD | not_started | Plan created 2026-03-18 |
| 21A | `21-provider-detection-from-providerid-field.md` | Extract providerID Field | TBD | TBD | TBD | not_started | Plan created 2026-03-18 |
| 21B | `21-provider-detection-from-providerid-field.md` | Data Integrity Verification | TBD | TBD | TBD | not_started | Plan created 2026-03-18 |

## Phase Milestones

| Milestone | Depends On | Target Date | Status | Notes |
|---|---|---|---|---|
| M1: Federation Registry Ready | 16A | 2026-03-17 | done | Completed in PR #1 |
| M2: Federated Fan-In Operational | 16B | 2026-03-18 | done | Completed in PR #15 |
| M3: Scope + Product Surface Integration | 16C, 16D | 2026-03-18 | done | Completed in PR #15 |
| M4: Provider Analytics Available | 17A, 17B, 17C, 17D | 2026-03-16 | done | Completed in PR #4 |
| M5: Update Check/Apply Available | 18A, 18B | 2026-03-15 | done | Completed in PR #3 |
| M6: Release Awareness + Docs Complete | 18C, 18D | 2026-03-15 | done | Completed in PRs #3, #6 |
| M7: Dashboard Source Management and Attribution Complete | 19A, 19B, 19C, 19D | 2026-03-18 | done | Completed in PR #15 |
| M8: Source Status Banner and Loading States | 20A, 20B | TBD | not_started | Plan created 2026-03-18 |
| M9: Provider Detection from providerID Field | 21A, 21B | TBD | not_started | Plan created 2026-03-18 |

## Weekly Checkpoint

| Week Of | Completed | In Progress | Blocked | Decisions Needed |
|---|---|---|---|---|
| 2026-03-09 | 18A, 18B, 18C, 18D | | | |
| 2026-03-16 | 17A, 17B, 17C, 17D, 16A | | | |
| 2026-03-17 | 16B, 16C, 16D, 19A, 19B, 19C, 19D | Plans 20, 21 created | | Decide implementation priority for Plans 20 vs 21 |
