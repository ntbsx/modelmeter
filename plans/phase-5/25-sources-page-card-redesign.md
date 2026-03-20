# 25. Sources Page Card Redesign

**Status:** Completed  
**Priority:** Medium  
**Dependencies:** None

## Problem Statement

The Sources page uses a wide table for listing source configuration and health states. This works functionally, but visual hierarchy is weak and mobile scanning is harder than needed.

## Goals

1. Replace source table listing with source cards.
2. Keep all current source actions (add, edit, remove, health check).
3. Improve readability of status, auth, and target connection details.
4. Preserve current behavior and API contracts.

## What Was Built

- Sources page listing converted from table to card layout.
- Each source card shows: identity (id, label, kind), connection target, auth status, enabled state, latest health state.
- Edit/remove actions preserved on each card.
- Global health check action preserved.
- Empty state improved.
- Card styling consistent with broader design system.

**Note:** Models, Providers, and Projects pages card conversions are handled separately in Plan 23 — they are NOT part of this plan.

## Acceptance Criteria

- [x] Source listing is card-based instead of table-based.
- [x] Add/edit/remove flows remain functional.
- [x] Health check states are clearly visible on cards.
- [x] Mobile and desktop layouts remain readable and stable.

## Validation

- `npm run --prefix web test -- --run` — 105 tests pass
- `npm run --prefix web build` — builds cleanly
- `uv run pytest tests/test_sources.py` — tests pass
