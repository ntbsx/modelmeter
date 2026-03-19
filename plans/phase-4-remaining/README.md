# Phase 4: Distributed Analytics and Lifecycle Automation (Remaining)

## Objective

Complete the final two plans of Phase 4:
- Source status banner and loading states for better UX
- Provider detection bug fix for data accuracy

## Background

Phase 4 Part 1 (Plans 16-19) was completed on 2026-03-18:
- ✅ Federation Core (Plan 16) - Multi-machine source federation
- ✅ Provider Analytics (Plan 17) - Provider-level reporting
- ✅ Auto-Update (Plan 18) - CLI update check/apply flow
- ✅ Dashboard Source Management (Plan 19) - Source registry and management

These features are already released in v2026.3.16 - v2026.3.21.

See `../completed/phase-4-part-1/phase-4-part-1-README.md` for detailed implementation notes.

## Remaining Plans (20-21)

### 20. Source Status Banner and Loading States

**Status:** Planned
**Priority:** High
**Estimated:** 4-5 hours
**Dependencies:** Plans 16, 19

**Problem:**
Users don't get visual feedback when:
- Switching between data sources
- Remote sources are unreachable
- Partial federation failures occur
- Data is loading

**Goals:**
- Loading indicators when switching sources
- Inactive source warnings
- Partial failure visibility
- Source scope indicator in page headers

**Key Changes:**
- New `SourceStatusBanner` component
- New `useSourceLabels` hook
- Integration across 7 data pages (Overview, Providers, Models, Projects, ProjectDetail, ModelDetail, Live)
- ModelDetail source scope support

**See Also:** `20-source-status-banner-and-loading-states.md`

---

### 21. Provider Detection from providerID Field

**Status:** Planned
**Priority:** High
**Estimated:** 4 hours
**Dependencies:** None

**Problem:**
ModelMeter ignores `providerID` field in message JSON, causing ~20% misattribution:
- 700 GitHub Copilot messages → wrong provider
- 2,569 OpenCode messages → marked as "unknown"

**Goals:**
- Extract `providerID` from message JSON
- Prioritize `providerID` over pattern matching
- Correctly attribute GitHub Copilot and OpenCode
- Maintain backwards compatibility

**Key Changes:**
- Update 8 repository methods to extract `provider_id`
- New provider detection function
- Update all analytics functions
- Add comprehensive tests

**See Also:** `21-provider-detection-from-providerid-field.md`

## Phase Exit Criteria

Phase 4 will be complete when:
- [ ] Plan 20 implemented and tested
- [ ] Plan 21 implemented and tested
- [ ] All tests pass
- [ ] CHANGELOG.md updated
- [ ] v2026.3.22 release tagged

## Dependencies

- Both plans depend on Phase 4 Part 1 completion (Plans 16-19)
- Plan 20 depends on federation and source management features
- Plan 21 is independent but should be completed with Phase 4

## Related

- **Archive:** `../completed/phase-4-part-1/` for Plans 16-19
- **Roadmap:** `../00-roadmap-index.md` for overall roadmap
- **Planning Guide:** `../README.md` for project-wide planning

## Historical Tracking

Previous tracking file (`TRACKING.md`) has been archived with Phase 4 Part 1.
See `../completed/phase-4-part-1/phase-4-part-1-README.md` for historical PR and milestone tracking.

## Next Steps After Phase 4

Once Plans 20-21 are complete:
1. Update CHANGELOG.md with Phase 4 completion notes
2. Tag and release v2026.3.22
3. Begin Phase 5 planning
4. Archive this folder to `../completed/phase-4-part-2/`
