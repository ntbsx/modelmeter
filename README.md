# ModelMeter

ModelMeter: OpenCode usage analytics for terminal and web.

## Installation

You can install ModelMeter globally using `pipx` or `uv tool`:

```bash
pipx install modelmeter
# OR
uv tool install modelmeter
```

Install from GitLab release archive via bash script (public project):

```bash
# Latest release
curl -fsSL https://gitlab.com/ntbsdev/modelmeter/-/raw/main/scripts/install.sh | bash

# Pinned release
curl -fsSL https://gitlab.com/ntbsdev/modelmeter/-/raw/main/scripts/install.sh | bash -s -- --version 2026.3.13
```

The installed package includes the built web UI, so `modelmeter serve` works without cloning the repo.
The installer prefers wheel assets published on the GitLab release page and falls back to source archives.

## Quick Start

```bash
# Terminal Commands
modelmeter doctor
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

If no local pricing file is provided, ModelMeter falls back to `models.dev` (the model directory used by OpenCode) and caches it at `~/.cache/modelmeter/models_dev_api.json`.

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

# Regenerate web API types from FastAPI OpenAPI
make gen-types

# Keep frontend + backend product versions aligned
make version-sync
make version-check

# Validate generated API types are up to date
npm run --prefix web check:types

# Quick bundle/API latency baseline
make perf-check
```

## Versioning

ModelMeter uses a **single product version** for backend, CLI, and frontend.

- Canonical source: `pyproject.toml` (`[project].version`)
- Canonical format: CalVer `YYYY.M.D` (example: `2026.3.13`)
- Frontend version in `web/package.json` must match backend version
- Runtime display version appends git short hash when available (`YYYY.M.D+<shortsha>`)
- OpenAPI schema version stays on canonical CalVer (without hash) for snapshot stability

Common version commands:

```bash
# Sync frontend version to backend version
make version-sync

# Stamp canonical CalVer from today and sync frontend
make version-stamp

# Check backend/frontend versions are aligned (non-zero exit on mismatch)
make version-check

# Enforce contract/version policy when OpenAPI changes
make contract-policy-check

# Full pre-release quality gate
make release-check
```

Contract policy (no API path versioning yet):

- API contract changes require updating canonical CalVer when preparing a release

### Web App (Local Dev)

You can run both the API backend and the React frontend simultaneously with one command:

```bash
make dev
```

Open your browser to `http://localhost:5173`.
OpenAPI docs are available at `http://127.0.0.1:8000/docs`.
Server docs alias is also available at `http://127.0.0.1:8000/doc`.

Live web monitoring uses server-sent events at `/api/live/events` and automatically falls back to polling if streaming is unavailable.
