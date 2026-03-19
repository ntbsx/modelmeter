# Feature Plan: Core Platform (DONE)

## Objective
Create a stable internal architecture that prevents rewrite when adding web later.

## Scope
- Python package layout under `src/modelmeter/`
- Core domain models and service boundaries
- Central configuration and path resolution
- Timezone and date-normalization utilities

## Deliverables
- `modelmeter.core` package (data contracts + service interfaces)
- `modelmeter.config` for env + CLI option resolution
- `modelmeter.common` helpers (time, formatting-safe primitives)
- Typed response models reusable by CLI and API

## Key Decisions
- Keep output rendering outside core
- Use Pydantic/dataclasses for normalized analytics payloads
- Support deterministic serialization for `--json` and API parity

## Acceptance Criteria
- Core can run without CLI/UI imports
- All analytics return structured models only
- Unit tests validate model schemas and serialization

## Tooling Baseline (Mandatory)
- Python: `>=3.12`
- Package/dependency/tool runner: `uv`
- Lint + format: `ruff` (`ruff check`, `ruff format`)
- Type checking: `pyright`
- Testing: `pytest` + `pytest-cov`
- Data models: `pydantic v2`
- CLI stack: `typer` + `rich`
- API stack (future-ready): `fastapi` + `uvicorn`

## Development Commands (Canonical)
- `uv sync`
- `uv run ruff format`
- `uv run ruff check`
- `uv run pyright`
- `uv run pytest`
