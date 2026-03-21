# 23. Card Layout, Infinite Scroll, and Charts

**Status:** Planned  
**Priority:** High  
**Dependencies:** 22-per-page-filters-and-date-insights.md

## Problem Statement

Models, Providers, and Projects rely on table-heavy views that feel flat and are harder to scan on mobile. Users requested card-based layouts, lazy loading, and stronger visual exploration with charts.

## Goals

1. Replace table-first list UIs with card-first feeds.
2. Add infinite scroll (lazy loading) for list-heavy pages.
3. Add charts on models/providers/projects pages for faster pattern recognition.
4. Preserve existing API pagination behavior (`offset`, `limit`) and keep scope/filter semantics consistent.

## Implementation Plan

### 1) Shared UI Primitives

- Add reusable card list building blocks for analytics entities.
- Add a reusable infinite-scroll hook/component using `IntersectionObserver`.
- Add common empty/loading/error card variants.

### 2) Models Page

- Convert rows to model cards.
- Add top-N chart (tokens/cost toggle).
- Implement lazy loading using existing `/api/models` pagination.

### 3) Providers Page

- Convert rows to provider cards.
- Add provider distribution chart.
- Implement lazy loading using `/api/providers` pagination.

### 4) Projects Page

- Convert rows to project cards.
- Add project distribution chart.
- Implement lazy loading using `/api/projects` pagination.

### 5) UX and Performance Constraints

- Keep card density readable on desktop and mobile.
- Avoid visual jumps during page append.
- Keep stable sort order across pages to prevent duplicate/missing cards.

## Acceptance Criteria

- [ ] Models/Providers/Projects no longer render primary table layouts.
- [ ] Infinite scroll loads additional pages correctly without duplicates.
- [ ] Charts are visible and useful on each of Models/Providers/Projects.
- [ ] Existing source scope and per-page time filters still apply correctly.
- [ ] Updated tests cover new card and pagination behaviors.

## Validation

- `npm run --prefix web test -- --run`
- `npm run --prefix web build`
