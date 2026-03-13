# Feature Plan: Packaging, Quality, and Observability (DONE)

## Objective
Ship reliably on macOS and Linux and keep regressions low.

## Scope
- `pyproject.toml` as single source of tool config
- `uv` for environment/dependency/task execution
- `ruff` for lint + format
- `pyright` for static type checks
- `pytest` + `pytest-cov` for tests
- `pre-commit` hooks for local quality gates
- Install via `pipx` (user-facing) and `uv tool` optional path
- Logging/diagnostics for supportability

## Deliverables
- Build and install docs
- CI pipeline (lint, type-check, tests)
- Golden JSON fixtures for analytics outputs
- `doctor` command with structured diagnostics
- Unified tool configuration in `pyproject.toml`:
  - `[tool.ruff]`
  - `[tool.pyright]` (or `pyrightconfig.json` if preferred)
  - `[tool.pytest.ini_options]`
- CI that runs:
  - `uv sync --frozen` (or locked equivalent)
  - `uv run ruff format --check`
  - `uv run ruff check`
  - `uv run pyright`
  - `uv run pytest --cov`

## Key Decisions
- Use pinned minimum supported Python version
- Keep dependency set lean
- Prefer deterministic tests with fixture DBs

## Acceptance Criteria
- Clean install + run on macOS and Linux
- CI green on supported versions
- Reproducible analytics outputs in tests
