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
uv sync
uv run ruff format
uv run ruff check
uv run pyright
uv run pytest
```

### Web App (Local Dev)

```bash
# Start backend API (Terminal 1)
uv run uvicorn modelmeter.api.app:app --reload

# Start frontend dev server (Terminal 2)
cd web
npm install
npm run dev
```

OpenAPI docs will be available at `http://127.0.0.1:8000/docs`.
