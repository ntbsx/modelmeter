# ModelMeter Feature Roadmap Index

ModelMeter: OpenCode usage analytics for terminal and web.

## Goal
Build a cross-platform (macOS + Linux) OpenCode usage monitor with:
- per-model usage
- daily token consumption
- cost analytics
- terminal-first UX
- web-ready architecture
- multi-machine federation
- provider-level insights

## Principles
- Shared core logic first (CLI and web use same analytics engine)
- Read-only access to OpenCode data
- SQLite-first with graceful legacy fallback
- Feature slices with clear acceptance criteria
- Modern Python toolchain baseline: uv + Ruff + Pyright + Pytest

## Active Roadmap

### Phase 4: Distributed Analytics and Lifecycle Automation (In Progress)

- [ ] 20. phase-4-remaining/20-source-status-banner-and-loading-states.md
  - Visual feedback for data loading and source failures
  - Priority: High
  - Estimated: 4-5 hours

- [ ] 21. phase-4-remaining/21-provider-detection-from-providerid-field.md
  - Fix provider detection bug (20% misattribution)
  - Priority: High
  - Estimated: 4 hours

## Completed Roadmap

### Phase 1-3: Core Platform and Initial Product (Completed 2026-03-15)

All foundational plans (01-09) completed. Archive: `completed/phase-1-3/`

Key milestones:
- Core platform, data layer, analytics engine
- CLI product with JSON output
- Live monitoring with SSE streaming
- API foundation for web consumption
- Web dashboard with visualization
- Packaging quality and observability

### Phase 4 Part 1: Distributed Analytics (Completed 2026-03-18)

Plans 16-19 completed. Archive: `completed/phase-4-part-1/`

Key milestones:
- Multi-machine source federation
- Provider-level analytics
- Auto-update and release awareness
- Dashboard source management

## Phase Exit Criteria

### Phase 1-3 (✅ Complete)
- CLI commands implemented with stable JSON output
- Live terminal monitoring functional
- API endpoints available with OpenAPI docs
- Web dashboard can consume API and display key metrics
- Packaging and tests pass on macOS and Linux

### Phase 4 Part 1 (✅ Complete)
- Multi-machine source federation works for CLI/API/Web
- Provider-level totals available and reconcile with model totals
- Users can check and apply updates from CLI
- Users can manage sources in dashboard with clear scope visibility

### Phase 4 Part 2 (🔄 In Progress)
- Source status banner and loading states implemented
- Provider detection bug fixed (0% misattribution)

## Future Phases

Plans for Phase 5 and beyond will be designed after Phase 4 completion.

Potential areas:
- Advanced federation features (ModelDetail, Live)
- Custom dashboards and saved queries
- Alerting and notifications
- Team/workspace management
- Integration with other AI tools

## Next Steps

1. Complete Plan 20: Source status banner and loading states
2. Complete Plan 21: Provider detection fix
3. Update CHANGELOG.md with Phase 4 completion
4. Tag v2026.3.22 release
5. Begin Phase 5 planning

## Quick Reference

- **Active Work:** `phase-4-remaining/`
- **Phase 1-3 Archive:** `completed/phase-1-3/phase-1-3-README.md`
- **Phase 4 Part 1 Archive:** `completed/phase-4-part-1/phase-4-part-1-README.md`
- **Planning Guide:** `README.md`
