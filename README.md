# ModelMeter

ModelMeter: usage analytics for AI coding agents — terminal and web.

## Installation

ModelMeter is currently distributed via GitHub Releases (not PyPI yet).

Install via the GitHub release installer script (public project).

Latest release:

```bash
curl -fsSL https://raw.githubusercontent.com/ntbsx/modelmeter/main/scripts/install.sh | bash
```

Pinned release:

```bash
curl -fsSL https://raw.githubusercontent.com/ntbsx/modelmeter/main/scripts/install.sh | bash -s -- --version 2026.3.16
```

Choose installation method explicitly if needed.

Prefer pipx:

```bash
curl -fsSL https://raw.githubusercontent.com/ntbsx/modelmeter/main/scripts/install.sh | bash -s -- --method pipx
```

Use pip --user:

```bash
curl -fsSL https://raw.githubusercontent.com/ntbsx/modelmeter/main/scripts/install.sh | bash -s -- --method pip
```

The installed package includes the built web UI, so `modelmeter serve` works without cloning the repo.
The installer prefers wheel assets published on the GitHub release page and falls back to source archives.

## Quick Start

```bash
# Terminal Commands
modelmeter doctor
modelmeter update check
modelmeter update check --json
modelmeter update apply --dry-run
modelmeter summary --days 7
modelmeter daily --days 7
modelmeter summary --days 7 --pricing-file ./models.json
modelmeter summary --days 7 --token-source steps
modelmeter summary --days 7 --session-source session
modelmeter models --days 7
modelmeter model openai/gpt-5.3-codex --days 7
modelmeter projects --days 7
modelmeter live --window-minutes 60

# Web Dashboard
modelmeter serve --port 8000

# Logging controls
modelmeter serve --log-level debug
modelmeter serve --no-access-log

# Allow additional web origins (repeatable)
modelmeter serve --cors http://localhost:5173 --cors https://app.example.com

# Optional basic auth for serve mode
MODELMETER_SERVER_PASSWORD=your-password modelmeter serve
MODELMETER_SERVER_USERNAME=custom-user MODELMETER_SERVER_PASSWORD=your-password modelmeter serve
```

### Web Login Experience

When `MODELMETER_SERVER_PASSWORD` is set, the web app uses a built-in login page instead of the browser's default Basic Auth modal.

- The frontend checks `/health` first and reads `auth_required`.
- If `auth_required` is `false`, the dashboard opens directly.
- If `auth_required` is `true`, users are sent to `/login` and sign in with Basic Auth credentials.
- Credentials are stored in browser `localStorage` (`modelmeter-auth`) until sign-out.

API behavior for auth-enabled mode:

- `/health` remains public and returns `status`, `app_version`, and `auth_required`.
- Protected API routes return `401` with JSON body `{"detail": "Invalid credentials"}`.

## Self-Update

ModelMeter can check for newer GitHub releases and prepare an install command:

```bash
# Check latest release vs current local version
modelmeter update check

# Machine-friendly output
modelmeter update check --json

# Preview install command without changing anything
modelmeter update apply --dry-run

# Apply a specific version
modelmeter update apply --version 2026.3.16
```

Update behavior can be configured with environment variables:

```bash
export MODELMETER_UPDATE_CHECK_ENABLED=true
export MODELMETER_UPDATE_CHECK_URL="https://api.github.com/repos/ntbsx/modelmeter/releases/latest"
export MODELMETER_UPDATE_CHECK_TIMEOUT_SECONDS=8
```

## Pricing File

You can provide model pricing via `--pricing-file` (or `MODELMETER_PRICING_FILE`).
Expected JSON shape (cost per 1M tokens):

```json
{
  "anthropic/claude-sonnet-4-5": {
    "input": 3.0,
    "output": 15.0,
    "cache_read": 0.3,
    "cache_write": 3.75
  }
}
```

If no local pricing file is provided, ModelMeter falls back to `models.dev` (the model directory used by OpenCode and Claude Code) and caches it at `~/.cache/modelmeter/models_dev_api.json`.

You can control this with environment variables:

```bash
export MODELMETER_PRICING_REMOTE_FALLBACK=true
export MODELMETER_PRICING_REMOTE_URL="https://models.dev/api.json"
export MODELMETER_PRICING_REMOTE_TIMEOUT_SECONDS=8
export MODELMETER_PRICING_CACHE_TTL_HOURS=24
```

## Development

```bash
# Setup both python and node dependencies
make setup

# Build frontend before serving backend
cd web && npm run build

# Run quality checks
make format
make lint
make typecheck
make test

# Run frontend tests
npm run --prefix web test
npm run --prefix web test:watch
npm run --prefix web test:coverage

# Regenerate web API types from FastAPI OpenAPI
make gen-types

# Keep frontend + backend product versions aligned
make version-sync
make version-check

# Validate generated API types are up to date
npm run --prefix web check:types

# Quick bundle/API latency baseline
make perf-check

# Enforce performance guardrail thresholds
make perf-guardrail
```

## CI and Releases

This repository uses GitHub Actions workflows:

- `.github/workflows/ci.yml` runs pull-request and `main` branch checks with a **truly parallel structure** for fast feedback (~69 seconds wall-clock time). Only `check_backend` (after lint) and `check_frontend` (after type generation) have dependencies; all other jobs run in parallel.
- `.github/workflows/release.yml` runs on version tags (`vYYYY.M.x` for stable, `vYYYY.M.xrcN` for prereleases) to validate version alignment, build release artifacts, run a package smoke test, and publish wheel/sdist assets to the GitHub release.

Before opening a PR, run:

```bash
make release-check
```

## Custom Commands (OpenCode)

This repo includes project-level OpenCode commands:

- `.opencode/commands/cleanup_local_branches.md`
- `.opencode/commands/create_release.md`

Use them from OpenCode TUI:

```bash
/cleanup-local-branches
/cleanup-local-branches apply
/cleanup-local-branches force

/create_release
/create_release dry-run stable
/create_release dry-run rc
/create_release apply stable
/create_release apply rc
```

Behavior:

- default (`dry-run`): show what would be deleted, no branch changes
- `apply`: delete local branches without an open PR using safe delete first (`git branch -d`)
- `force`: if safe delete fails, force-delete remaining non-PR branches (`git branch -D`)
- protected branches are never deleted: `main`, `master`, `develop`, and current branch
- command requires `gh` CLI installed and authenticated (`gh auth status`)

Release command behavior:

- default (`dry-run stable`): show release plan without changes
- `stable`: only allowed from `main`
- `rc`: allowed from any branch, including `main`
- `apply`: stamps/checks/commits/tags/pushes and triggers `.github/workflows/release.yml`

## Versioning

ModelMeter uses a **single product version** for backend, CLI, and frontend.

- Canonical source: `pyproject.toml` (`[project].version`)
- Canonical stable format: CalVer `YYYY.M.x` (example: `2026.3.17`)
- Canonical prerelease format: `YYYY.M.xrcN` (example: `2026.3.17rc2`)
- Frontend version in `web/package.json` must match backend version
- Runtime display version appends git short hash when available (`YYYY.M.x+<shortsha>`)
- OpenAPI schema version stays on canonical CalVer (without hash) for snapshot stability

Release tag/version alignment:

- Stable release tags use `vYYYY.M.x` and must match `pyproject.toml` and `web/package.json`.
- Prerelease tags use `vYYYY.M.xrcN`.
- For prereleases, `pyproject.toml` and `web/package.json` stay on base version (`YYYY.M.x`) in git; the release workflow applies the `rc` suffix in CI before packaging.

Common version commands:

```bash
# Sync frontend version to backend version
make version-sync

# Bump canonical monthly patch CalVer and sync frontend
make version-stamp

# Check backend/frontend versions are aligned (non-zero exit on mismatch)
make version-check

# Enforce contract/version policy when OpenAPI changes
make contract-policy-check

# Full pre-release quality gate
make release-check

# Build release artifacts (wheel/sdist with bundled web assets)
make package-build
```

Contract policy (no API path versioning yet):

- API contract changes require updating canonical CalVer when preparing a release

Release workflow reference: `docs/release-runbook.md`

### Web App (Local Dev)

You can run both the API backend and the React frontend simultaneously with one command:

```bash
make dev
```

Open your browser to `http://localhost:5173`.
OpenAPI docs are available at `http://127.0.0.1:8000/docs`.
Server docs alias is also available at `http://127.0.0.1:8000/doc`.

Live web monitoring uses server-sent events at `/api/live/events` and automatically falls back to polling if streaming is unavailable.

When auth is enabled, SSE in browsers may fall back to polling because `EventSource` does not support custom Authorization headers.

## Web Dashboard Features

The web dashboard provides visual analytics for your AI coding agent usage:

- **Overview**: Summary stats and daily usage trend chart with tokens, sessions, and cost
- **Models**: Usage breakdown by model with drill-down to model detail pages
- **Projects**: Usage breakdown by project with session-level detail
- **Live**: Real-time monitoring with active session info and rolling window stats

All views support flexible time range filtering with presets (24h, 7d, 30d, 90d) or custom date ranges.

## Testing

Backend tests use pytest:

```bash
# Run all backend tests
make test

# Run specific test file
uv run pytest tests/test_api.py

# Run specific test
uv run pytest tests/test_api.py::test_health_endpoint
```

Frontend tests use Vitest with React Testing Library:

```bash
# Run all frontend tests
npm run --prefix web test

# Run in watch mode
npm run --prefix web test:watch

# Run with coverage
npm run --prefix web test:coverage
```
