# Feature Plan: Terminal CLI Product (DONE)

## Objective
Deliver a polished terminal app as the first user-facing product.

## Scope
- Commands: `summary`, `daily`, `models`, `model`, `projects`, `doctor`
- Rich table UX + machine-readable JSON mode
- Filter flags (days/date-range/project/model)
- Exit codes and clear error handling

## Deliverables
- Typer command surface
- Rich renderers separated from analytics core
- `--json` on all data commands
- Consistent command help and examples
- CLI implemented with `typer` and `rich` on top of shared core
- All commands runnable via `uv run modelmeter ...`

## Key Decisions
- CLI commands call shared services only (no direct SQL in command handlers)
- Output schema consistency between text and json modes
- Human-friendly defaults; explicit flags for advanced filtering

## Acceptance Criteria
- Each command has deterministic output and tests
- `--json` is consumable by scripts without extra text noise
- Help output documents all key examples
- CLI commands pass lint/type/test gates under uv workflow
