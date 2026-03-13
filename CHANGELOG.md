# Changelog

All notable changes to ModelMeter are documented in this file.

The format follows Keep a Changelog and versions follow project CalVer (`YYYY.M.D`).

## [Unreleased]

### Added
- Added project detail page with per-session usage visibility in the web app.
- Added route-level code splitting for major frontend pages.
- Added package bundling workflow for web assets and a public GitLab installer script.

### Changed
- Migrated canonical product versioning to CalVer.
- Added runtime display version with optional short git hash suffix.
- Updated CI to include frontend lint and packaging smoke checks.

### Fixed
- Fixed web version badge fetch path to use `/health`.
- Fixed OpenAPI snapshot instability by excluding SPA fallback route from schema.
- Fixed CI dependency and runtime issues for pyright/pytest jobs.
