# AGENTS Guide for ModelMeter
This guide is for coding agents operating in this repository.

## 1) Project Snapshot
- Backend: Python 3.12, FastAPI, Typer, Pydantic.
- Frontend: React 19, TypeScript, Vite, Tailwind v4.
- Python tooling: `uv`; frontend tooling: `npm` in `web/`.
- Key directories:
  - `src/modelmeter/` backend + CLI
  - `tests/` Python tests
  - `web/src/` frontend code

## 2) Cursor/Copilot Rules Check
Checked at time of writing:
- `.cursorrules`: not found
- `.cursor/rules/`: not found
- `.github/copilot-instructions.md`: not found
If these files are added later, fold their guidance into this document.

## 3) Setup
Run from repo root:

```bash
make setup
```

Equivalent manual setup:

```bash
uv sync
npm install --prefix web
```

## 4) Build / Lint / Typecheck / Test Commands
Primary commands (Makefile):
- `make dev` run backend + frontend dev servers
- `make backend` run FastAPI (`uvicorn`) on `:8000` with reload
- `make frontend` run Vite dev server
- `make format` run `ruff format`
- `make lint` run `ruff check`
- `make typecheck` run `pyright` (strict)
- `make test` run all pytest tests
- `make gen-types` regenerate OpenAPI + TS generated types
- `make version-sync` sync `web/package.json` version from `pyproject.toml`
- `make version-check` fail on backend/frontend version mismatch

Frontend scripts:
- `npm run --prefix web dev`
- `npm run --prefix web build`
- `npm run --prefix web lint`
- `npm run --prefix web preview`
- `npm run --prefix web gen:types`
- `npm run --prefix web check:types`

Note: no dedicated frontend unit test runner is configured right now.

## 5) Product Versioning (Single Version)
- ModelMeter uses a single SemVer product version across backend, CLI, and frontend.
- Canonical source of truth: `pyproject.toml` in `[project].version`.
- Frontend version in `web/package.json` must match backend version.
- Runtime backend version is derived from package metadata/project config, not a separate hardcoded constant.
- Use:
  - `make version-sync` to align frontend version to backend version
  - `make version-check` to fail fast when versions diverge

## 6) Running a Single Test (Important)
Use targeted pytest while iterating:

```bash
# single file
uv run pytest tests/test_api.py

# single test function
uv run pytest tests/test_api.py::test_health_endpoint

# by keyword expression
uv run pytest -k "health and not auth"
```

Helpful flags:
- `-q` quiet output
- `-x` stop on first failure
- `-vv` verbose test IDs

## 7) OpenAPI and Generated Artifacts
- OpenAPI snapshot: `web/openapi.json`
- Generated TS types: `web/src/generated/api.ts`
- Snapshot hash: `web/src/generated/openapi.sha256`

Regenerate contract artifacts:

```bash
make gen-types
```

Verify generated artifacts are up to date:

```bash
npm run --prefix web check:types
```

Do not hand-edit files under `web/src/generated/`.

## 8) Python Style Guidelines
Formatting and imports:
- Ruff is source of truth for format/lint.
- Max line length: 100 (`pyproject.toml`).
- Keep imports sorted/grouped (Ruff `I` rules).
- Prefer absolute imports from `modelmeter.*`.

Typing:
- Pyright strict mode is enabled; maintain complete type hints.
- Add explicit return types for public functions.
- Use `Literal` and narrow unions where they improve safety.
- Prefer `Path` for filesystem values in backend internals.

Naming and architecture:
- Files/modules/functions/variables: `snake_case`.
- Classes/Pydantic models: `PascalCase`.
- Constants: `UPPER_SNAKE_CASE`.
- Separation of concerns:
  - `api/` HTTP routes + HTTP error mapping
  - `core/` business/domain logic
  - `data/` persistence/integration
  - `config/` settings and environment mapping

Error handling:
- Raise meaningful errors in lower layers.
- Convert runtime/domain failures to `HTTPException` at API boundary.
- Avoid broad silent catches.
- CLI should print actionable errors and exit non-zero on fatal failures.

Comments/docstrings:
- Prefer clear names over comments.
- Add comments only for non-obvious intent.
- Keep docstrings concise and factual.

## 9) Frontend Style Guidelines
- TypeScript is strict; avoid `any` unless unavoidable.
- Keep API helpers in `web/src/lib/`.
- Keep route-level UI in `web/src/pages/`.
- Components use `PascalCase` naming.
- Prefer generated OpenAPI types over ad-hoc types.
- If API contracts change, regenerate snapshot/types/hash together.

## 10) Testing Expectations
- Backend behavior changes should update/add pytest coverage.
- API schema changes must update OpenAPI artifacts and related tests.
- Run targeted tests first, then broader checks before final handoff.
- Useful suites:
  - `tests/test_api.py`
  - `tests/test_openapi_contract.py`
  - `tests/test_versioning.py`

## 11) Pre-commit Alignment
Configured hooks in `.pre-commit-config.yaml`:
- `ruff-format`
- `ruff --fix`
- `pyright`

Recommended pre-PR command:

```bash
make format && make lint && make typecheck && make test
```

## 12) Agent Workflow Expectations
- Make minimal, scoped edits.
- Do not modify unrelated files.
- Respect generated-file boundaries.
- Start with smallest relevant verification, then widen coverage.
- Update docs when changing developer workflows.
