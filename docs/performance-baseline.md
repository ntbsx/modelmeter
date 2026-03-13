# Performance Baseline

This document tracks lightweight performance signals to catch regressions early.

## Baseline Inputs

- Frontend production bundle sizes from `web/dist/assets`
- API in-process `/health` latency samples (30 requests)

## Command

```bash
npm run --prefix web build
uv run python scripts/perf_baseline.py
```

## Suggested Review Cadence

- Before each release tag
- After adding heavy frontend dependencies (charts/editors/data grids)
- After changing analytics query paths

## Suggested Thresholds

- Largest JS chunk: keep below 450 KB (non-gzipped) unless justified
- `/health` avg in-process latency: keep below 20 ms on dev machine

Thresholds are heuristics and should be adjusted as the product grows.
