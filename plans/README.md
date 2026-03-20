# ModelMeter Planning Guide for Agents

This folder contains **active and planned** features for ModelMeter (OpenCode usage analytics for terminal and web).

## Current Structure

- **Active Plans:** Current plans directory contains only active/planned work
- **Completed Plans:** Historical plans archived in `completed/` folder by phase
- **Execution Order:** Follow dependencies and checkpoints outlined below

## Active Work

### Phase 5: Analytics UX and Exploration (In Progress)

- [ ] `phase-5/22-per-page-filters-and-date-insights.md`
  - Status: Planned
  - Priority: High
  - Estimated: 6-8 hours
  - Description: Move date filters to each page, add date-specific spend breakdown, and add auth-disabled warning (web + terminal)

- [ ] `phase-5/23-card-layout-infinite-scroll-and-charts.md`
  - Status: Planned
  - Priority: High
  - Estimated: 8-12 hours
  - Description: Replace table-heavy list views with card feeds, lazy loading, and charts

- [ ] `phase-5/24-live-multi-session-and-scope-simplification.md`
  - Status: Planned
  - Priority: High
  - Estimated: 6-10 hours
  - Description: Add multi-session live panels (local or server self) and remove ineffective live-only source selector behavior

- [ ] `phase-5/25-sources-page-card-redesign.md`
  - Status: Planned
  - Priority: Medium
  - Estimated: 4-6 hours
  - Description: Redesign Sources listing into cards while keeping source management flows intact

### Phase Milestones

- **Phase 1-3:** ✅ Complete (Core Platform, Analytics, CLI, Web)
- **Phase 4 Part 1:** ✅ Complete (Federation, Provider Analytics, Update Flow, Source Management)
- **Phase 4 Part 2:** ✅ Complete (Plans 20-21)
- **Phase 5:** 🔄 In Progress (Plans 22-25)

## Completed Work

Historical plans are organized in `completed/` by phase:

- **`completed/phase-1-3/`** - Foundation plans (01-09)
  - Core Platform, Data Layer, Analytics Engine
  - CLI Product, Live Monitoring
  - API Foundation, Web App
  - Packaging Quality, Future Extensions
  - See `phase-1-3-README.md` for details

- **`completed/phase-4_part_1/`** - First half of Phase 4 (16-19)
  - Federation Core, Provider Analytics
  - Auto-Update & Release Awareness
  - Dashboard Source Management
  - See `completed/phase-4_part_1/phase-4-part-1-README.md` for details

- **`completed/phase-4_part_2/`** - Second half of Phase 4 (20-21)
  - Source status banner and loading states
  - Provider detection from providerID field
  - See `completed/phase-4_part_2/README.md` for details

## Engineering Standards (Applies to all phases)

- Use `uv` for all dependency and command execution
- Use `ruff` as single formatter/linter
- Enforce typing with `pyright`
- Enforce tests with `pytest`
- Keep all tool settings centralized in `pyproject.toml`

## Dependency Graph (Active Work Only)

- `22-per-page-filters-and-date-insights` → foundation for page-local data flow and date drill-down UX
- `23-card-layout-infinite-scroll-and-charts` → depends on `22` for page-local filter ownership
- `24-live-multi-session-and-scope-simplification` → can run in parallel with `23` after `22`
- `25-sources-page-card-redesign` → independent, can run in parallel with `23`/`24`

## Definition of Done (Current Phase)

- [ ] Per-page time filters implemented across target analytics pages
- [ ] Date insights page supports one-day spend and token analysis by model/provider/project
- [ ] Models/Providers/Projects migrated to cards with lazy loading and charts
- [ ] Live page supports multi-session panels on local/server (self) with simplified scope UX
- [ ] Sources page migrated to card-based listing
- [ ] Frontend and backend validation suites pass

## Quick Reference

- **Current Version:** See `pyproject.toml` `[project].version`
- **Latest Release:** See `git describe --tags --abbrev=0`
- **Roadmap Index:** See `00-roadmap-index.md`
- **Phase 4 Tracking:** See `completed/phase-4_part_2/README.md`
- **Phase 5 Tracking:** See `phase-5/README.md`

## Historical Dependency Graph (Archived)

For reference on how completed phases were structured, see the archive READMEs:

- **Phase 1-3 dependencies:**
  - `01` → foundation for all other plans
  - `02` → depends on `01`
  - `03` → depends on `01`, `02`
  - `04` → depends on `03`
  - `05` → depends on `02`, `03`, and parts of `04`
  - `06` → depends on `03`
  - `07` → depends on `06`
  - `08` → cross-cutting, starts early, finalizes late
  - `09` → after `04`, `06`, and `07` baseline completion
  - `10` → after `06` and `07`, before or alongside `09`
  - `11` → depends on `07`, `08`, and `10`
  - `12` → depends on `14` and `15`
  - `13` → depends on `03`, `04`, `06`, and `07`
  - `14` → depends on `12` and `13`
  - `15` → depends on `12`, `13`, and `14`

- **Phase 4 Part 1 dependencies:**
  - `16-federation-core` → depends on `03`, `04`, `06`, and `10`
  - `17-provider-analytics` → depends on `03`, `06`, and `16`
  - `18-auto-update-and-release-awareness` → depends on `14` and `15`
  - `19-dashboard-source-management-and-filtering` → depends on `07`, `10`, `11`, and `16`

See archive README files for detailed execution order and parallelization strategies.
