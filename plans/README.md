# ModelMeter Planning Guide for Agents

This folder contains **active and planned** features for ModelMeter (OpenCode usage analytics for terminal and web).

## Current Structure

- **Active Plans:** Current plans directory contains only active/planned work
- **Completed Plans:** Historical plans archived in [completed/](completed/) folder by phase
- **Execution Order:** Follow dependencies and checkpoints outlined below

## Active Work

### Phase 6: Multi-Agent Support — Claude Code Integration (Active)

Plans in [phase-6/](phase-6/) (Plans 27-32). See [phase-6/README.md](phase-6/README.md) for details.

### Phase Milestones

- **Phase 1-3:** ✅ Complete (Core Platform, Analytics, CLI, Web)
- **Phase 4 Part 1:** ✅ Complete (Federation, Provider Analytics, Update Flow, Source Management)
- **Phase 4 Part 2:** ✅ Complete (Plans 20-21)
- **Phase 5:** ✅ Complete (Plans 22-26 all done)
- **Phase 6:** 🔄 Active (Plans 27-32)

## Completed Work

Historical plans are organized in [completed/](completed/) by phase:

- **[completed/phase-1-3/](completed/phase-1-3/)** - Foundation plans (01-09)
  - Core Platform, Data Layer, Analytics Engine
  - CLI Product, Live Monitoring
  - API Foundation, Web App
  - Packaging Quality, Future Extensions
  - See [phase-1-3-README.md](completed/phase-1-3/phase-1-3-README.md) for details

- **[completed/phase-4_part_1/](completed/phase-4_part_1/)** - First half of Phase 4 (16-19)
  - Federation Core, Provider Analytics
  - Auto-Update & Release Awareness
  - Dashboard Source Management
  - See [phase-4-part-1-README.md](completed/phase-4_part_1/phase-4-part-1-README.md) for details

- **[completed/phase-4_part_2/](completed/phase-4_part_2/)** - Second half of Phase 4 (20-21)
  - Source status banner and loading states
  - Provider detection from providerID field
  - See [README.md](completed/phase-4_part_2/README.md) for details

## Engineering Standards (Applies to all phases)

- Use `uv` for all dependency and command execution
- Use `ruff` as single formatter/linter
- Enforce typing with `pyright`
- Enforce tests with `pytest`
- Keep all tool settings centralized in `pyproject.toml`

## Dependency Graph (Active Work Only)

- `27-repository-protocol-and-factory` → foundation for all Phase 6 work
- `28-claudecode-jsonl-reader` → depends on `27`
- `29-auto-detection-and-agent-identity` → depends on `28`
- `30-analytics-multi-repo-integration` → depends on `29`
- `31-live-monitoring-claudecode` → depends on `30`
- `32-frontend-agent-identity` → depends on `31`

## Definition of Done (Current Phase — Phase 6)

- [ ] UsageRepository Protocol defined; SQLiteUsageRepository satisfies it
- [ ] JsonlUsageRepository reads Claude Code JSONL data with full method coverage
- [ ] Auto-detection discovers both OpenCode and Claude Code data on startup
- [ ] Agent identity field on sources; API responses include agent metadata
- [ ] All analytics endpoints include Claude Code data when present
- [ ] Live monitoring shows active Claude Code sessions
- [ ] Doctor reports multi-agent detection status
- [ ] Frontend displays agent identity on source/session cards
- [ ] All existing tests pass; new tests cover JSONL reader and multi-agent
- [ ] OpenAPI artifacts regenerated for schema changes

## Quick Reference

- **Current Version:** See `pyproject.toml` `[project].version`
- **Latest Release:** See `git describe --tags --abbrev=0`
- **Roadmap Index:** [00-roadmap-index.md](00-roadmap-index.md)
- **Phase 5 Archive:** [completed/phase-5/README.md](completed/phase-5/README.md)
- **Phase 6 Plans:** [phase-6/README.md](phase-6/README.md)

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
