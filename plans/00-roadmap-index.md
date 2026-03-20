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

### Phase 4: Distributed Analytics and Lifecycle Automation (Completed 2026-03-19)

All plans (16-21) completed. Archive: `completed/phase-4_part_1/` and `completed/phase-4_part_2/`

Key milestones:
- Multi-machine source federation
- Provider-level analytics
- Auto-update and release awareness
- Dashboard source management
- Source status banner and loading states
- Provider detection from providerID field (fixes 20% misattribution)

## Phase Exit Criteria

### Phase 1-3 (✅ Complete)
- CLI commands implemented with stable JSON output
- Live terminal monitoring functional
- API endpoints available with OpenAPI docs
- Web dashboard can consume API and display key metrics
- Packaging and tests pass on macOS and Linux

### Phase 4 (✅ Complete)
- Multi-machine source federation works for CLI/API/Web
- Provider-level totals available and reconcile with model totals
- Users can check and apply updates from CLI
- Users can manage sources in dashboard with clear scope visibility
- Source status banner provides visual feedback during loading/source issues
- Provider detection uses providerID field (0% misattribution)

## Future Phases

Plans for Phase 5 and beyond will be designed after Phase 4 completion.

Potential areas:
- Advanced federation features (ModelDetail, Live)
- Custom dashboards and saved queries
- Alerting and notifications
- Team/workspace management
- Integration with other AI tools

## Quick Reference

- **Phase 1-3 Archive:** `completed/phase-1-3/phase-1-3-README.md`
- **Phase 4 Part 1 Archive:** `completed/phase-4_part_1/phase-4-part-1-README.md`
- **Phase 4 Part 2 Archive:** `completed/phase-4_part_2/`
- **Planning Guide:** `README.md`
