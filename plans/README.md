# ModelMeter Planning Guide for Agents

This folder contains feature-sliced plans for building ModelMeter (OpenCode usage analytics for terminal and web).

## Engineering Standards (Applies to all phases)
- Use `uv` for all dependency and command execution.
- Use `ruff` as the single formatter/linter.
- Enforce typing with `pyright`.
- Enforce tests with `pytest`.
- Keep all tool settings centralized in `pyproject.toml`.

## Execution Order (Primary Path)
- [x] `01-core-platform.md`
- [x] `02-opencode-data-layer.md`
- [x] `03-analytics-engine.md`
- [x] `04-cli-product.md`
- [x] `05-live-monitoring.md`
- [x] `06-api-foundation-for-web.md`
- [x] `07-web-app-plan.md`
- [x] `08-packaging-quality-observability.md`
- [x] `09-future-extensions.md`
- [x] `10-server-parity-contract-live-streaming.md`
- [x] `11-frontend-product-polish-and-reliability.md`
- [x] `12-release-ops-and-collaboration-hardening.md`
- [ ] `13-performance-and-scalability.md`
- [x] `14-release-artifact-packaging-and-installer.md`
- [x] `15-calver-and-git-hash-versioning.md`

Use `00-roadmap-index.md` as the high-level map.

## Dependency Graph (What depends on what)
- `01-core-platform` -> foundation for all other plans
- `02-opencode-data-layer` -> depends on `01`
- `03-analytics-engine` -> depends on `01`, `02`
- `04-cli-product` -> depends on `03`
- `05-live-monitoring` -> depends on `02`, `03`, and parts of `04` rendering patterns
- `06-api-foundation-for-web` -> depends on `03`
- `07-web-app-plan` -> depends on `06`
- `08-packaging-quality-observability` -> cross-cutting, starts early, finalizes late
- `09-future-extensions` -> after `04`, `06`, and `07` baseline completion
- `10-server-parity-contract-live-streaming` -> after `06` and `07`, before or alongside `09`

## Parallelization Strategy
After `01` is complete:
- Track A: `02` -> `03`
- Track B: start scaffolding from `08` (tooling/CI/tests skeleton), without locking analytics contracts
- Track C: early UX shell for `04` can begin, but final command behavior must wait for `03`

After `03` is stable:
- Run `04` and `06` in parallel
- Start `05` in parallel with `04` once live snapshot contract exists
- Start `07` once `06` endpoint contracts are stable

## Contract Freeze Checkpoints
To avoid rework, freeze these contracts before downstream work:
1. Core analytics models (`01` + `03`)
2. Data-layer normalized record shape (`02`)
3. CLI JSON output schema (`04`)
4. API response schema parity with CLI JSON (`06`)

## Definition of Done (Roadmap Level)
- [x] CLI commands implemented with stable JSON output
- [x] Live terminal monitoring functional
- [x] API endpoints available with OpenAPI docs
- [x] Web dashboard can consume API and display key metrics
- [x] Packaging and tests pass on macOS and Linux
