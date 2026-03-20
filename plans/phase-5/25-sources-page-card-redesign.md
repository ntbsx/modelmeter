# 25. Sources Page Card Redesign

**Status:** Planned  
**Priority:** Medium  
**Dependencies:** None

## Problem Statement

The Sources page uses a wide table for listing source configuration and health states. This works functionally, but visual hierarchy is weak and mobile scanning is harder than needed.

## Goals

1. Replace source table listing with source cards.
2. Keep all current source actions (add, edit, remove, health check).
3. Improve readability of status, auth, and target connection details.
4. Preserve current behavior and API contracts.

## Implementation Plan

### 1) Card Listing Layout

- Convert each source row into a card with sections:
  - identity (id, label, kind)
  - connection target
  - auth status
  - enabled state
  - latest health state

### 2) Action Model

- Keep edit/remove actions on each card.
- Keep global health check action.
- Keep existing add/edit form flow.

### 3) State and Feedback

- Preserve stored health behavior from local storage.
- Keep healthy/unreachable indicator clarity.
- Improve empty-state presentation for zero sources.

## Acceptance Criteria

- [ ] Source listing is card-based instead of table-based.
- [ ] Add/edit/remove flows remain functional.
- [ ] Health check states are clearly visible on cards.
- [ ] Mobile and desktop layouts remain readable and stable.

## Validation

- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
- `uv run pytest tests/test_sources.py`
