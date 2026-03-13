# ModelMeter

ModelMeter: OpenCode usage analytics for terminal and web.

## Installation

You can install ModelMeter globally using `pipx` or `uv tool`:

```bash
pipx install modelmeter
# OR
uv tool install modelmeter
```

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

# Validate generated API types are up to date
npm run --prefix web check:types
```

### Web App (Local Dev)

You can run both the API backend and the React frontend simultaneously with one command:

```bash
make dev
```

Open your browser to `http://localhost:5173`.
OpenAPI docs are available at `http://127.0.0.1:8000/docs`.
Server docs alias is also available at `http://127.0.0.1:8000/doc`.

Live web monitoring uses server-sent events at `/api/live/events` and automatically falls back to polling if streaming is unavailable.
