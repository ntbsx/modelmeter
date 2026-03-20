# Changelog

All notable changes to ModelMeter are documented in this file.

The format follows Keep a Changelog and versions follow project CalVer (`YYYY.M.D`).

## [Unreleased]

## [2026.3.23] - 2026-03-20

### Changed
- Bumped frontend dev dependency `flatted`.

### Fixed
- Stabilized mobile bottom navigation so the scope selector no longer shifts the logout action.
- Updated mobile scope icon styling to match other bottom navigation items.

## [2026.3.22] - 2026-03-20

### Added
- `/create_release` OpenCode command to automate stable and release-candidate preparation.
- Source status banner and loading states in the web dashboard.

### Changed
- Improved web dashboard UX quality with hardening, polish, and responsive behavior updates.
- Optimized SQLite analytics query performance with caching and targeted PRAGMA tuning.

### Fixed
- Corrected `sources_considered` completeness in federated responses.
- Resolved frontend TypeScript strict-nullability issues on analytics pages.
- Replaced environment-dependent federation tests with CI-safe test behavior.

## [2026.3.21] - 2026-03-19

### Added
- Comprehensive design system implementation across frontend with unified color tokens, spacing, and typography.
- `/create_pr` command for standardized pull request creation.
- Chart color alignment with design system tokens.

### Changed
- Improved UX indicators and visual feedback across the dashboard.
- Enhanced mobile experience with improved logout flow.

### Fixed
- CSS token alignment for chart and purple color scales.
- DataTable row accessibility with proper ARIA roles.
- Command file naming consistency (snake_case).

## [2026.3.18] - 2026-03-16

### Added
- Provider analytics page with drill-down views in web dashboard.
- Open source community files: CONTRIBUTING.md, issue templates, enhanced .gitignore.

### Changed
- Migrated CI workflows to GitHub Actions with Node 24 runtime.
- Aligned release versioning with PEP 440 rc tag format.

## [2026.3.17] - 2026-03-15

### Added
- Custom login page for web dashboard auth, replacing browser basic auth modal.
- Release update check and apply flow via CLI (`modelmeter update check`, `modelmeter update apply`).

### Changed
- Migrated CI from GitLab to GitHub Actions workflows.
- Migrated installer and updater to GitHub Releases.

## [2026.3.16] - 2026-03-14

### Fixed
- Fixed release publishing job payload handling for the GitHub Releases API.
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
- Distribution via GitHub Releases with installer script.

### Fixed
- Fixed web version badge fetch path to use `/health`.
- Fixed OpenAPI snapshot instability by excluding SPA fallback route from schema.
- Fixed CI dependency and runtime issues for pyright/pytest jobs.
- Fixed frontend lint issues in test helpers and utility tests for release readiness.
