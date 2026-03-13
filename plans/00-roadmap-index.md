# ModelMeter Feature Roadmap Index

ModelMeter: OpenCode usage analytics for terminal and web.

## Goal
Build a cross-platform (macOS + Linux) OpenCode usage monitor with:
- per-model usage
- daily token consumption
- cost analytics
- terminal-first UX
- web-ready architecture

## Principles
- Shared core logic first (CLI and web use same analytics engine)
- Read-only access to OpenCode data
- SQLite-first with graceful legacy fallback
- Feature slices with clear acceptance criteria
- Modern Python toolchain baseline: uv + Ruff + Pyright + Pytest

## Roadmap Files
- [x] 1. 01-core-platform.md
- [x] 2. 02-opencode-data-layer.md
- [x] 3. 03-analytics-engine.md
- [x] 4. 04-cli-product.md
- [x] 5. 05-live-monitoring.md
- [x] 6. 06-api-foundation-for-web.md
- [x] 7. 07-web-app-plan.md
- [x] 8. 08-packaging-quality-observability.md
- [x] 9. 09-future-extensions.md
- [x] 10. 10-server-parity-contract-live-streaming.md
