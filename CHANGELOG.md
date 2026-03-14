# Changelog

All notable changes to ModelMeter are documented in this file.

The format follows Keep a Changelog and versions follow project CalVer (`YYYY.M.D`).

## [Unreleased]

### Added
- Placeholder for upcoming changes.

## [2026.3.16] - 2026-03-14

### Fixed
- Fixed GitLab release publishing job to send valid JSON payload to the Releases API.
- Fixed release/version mismatch by aligning package versioning with the release tag flow.

## [2026.3.14] - 2026-03-14

### Added
- Initial public release of ModelMeter.
- Backend API with summary, daily usage, models, model detail, projects, project detail, live snapshot, and live events endpoints.
- CLI commands for doctor, summary, daily, models, model detail, projects, live monitoring, server mode, and environment info.
- Web dashboard pages for overview, models, model detail, projects, project detail, and live monitoring.
- Interactive dashboards with usage charts, model/project breakdowns, and per-session visibility.
- Time-window filtering with presets and custom day counts.
- Optional pricing integration via local pricing files and remote `models.dev` fallback with caching.
- Optional server basic auth and configurable CORS for hosted dashboard usage.
- Frontend testing setup with Vitest and React Testing Library.
- Distribution and installation support via packaged wheel/sdist with bundled web assets and installer script.

### Changed
- Migrated canonical product versioning to CalVer.
- Added runtime display version with optional short git hash suffix.
- Updated CI to include frontend lint and packaging smoke checks.
- Updated README and AGENTS docs with frontend testing and dashboard feature guidance.
- Standardized OpenAPI snapshot and generated TypeScript contract workflow for frontend/backend parity.

### Fixed
- Fixed web version badge fetch path to use `/health`.
- Fixed OpenAPI snapshot instability by excluding SPA fallback route from schema.
- Fixed CI dependency and runtime issues for pyright/pytest jobs.
- Fixed frontend lint issues in test helpers and utility tests for release readiness.
