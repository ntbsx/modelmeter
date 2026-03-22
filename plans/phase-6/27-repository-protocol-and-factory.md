# 27. Repository Protocol and Factory

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extract a `UsageRepository` Protocol from `SQLiteUsageRepository`, define a `RowDict` type alias, adapt `SQLiteUsageRepository` to return dicts, and create a factory function.

**Architecture:** Introduce a formal Protocol that both existing SQLite and future JSONL readers implement. Add a `_to_dict` conversion to `SQLiteUsageRepository` so all methods return `dict[str, Any]` instead of `sqlite3.Row`. Generalize `_token_usage_from_row` in analytics and live to accept dicts.

**Tech Stack:** Python, typing.Protocol, Pyright strict

---

### Task 1: Define RowDict type alias and UsageRepository Protocol

**Files:**
- Create: `src/modelmeter/data/repository.py`
- Test: `tests/test_repository_protocol.py`

- [ ] **Step 1: Write the failing test**

```python
# tests/test_repository_protocol.py
"""Verify SQLiteUsageRepository satisfies UsageRepository Protocol."""

from modelmeter.data.repository import UsageRepository


def test_protocol_exists() -> None:
    """UsageRepository should be importable as a Protocol."""
    assert hasattr(UsageRepository, "__protocol_attrs__") or callable(UsageRepository)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_repository_protocol.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'modelmeter.data.repository'`

- [ ] **Step 3: Write the Protocol and RowDict**

Create `src/modelmeter/data/repository.py`:

```python
"""Repository protocol and factory for usage data readers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

RowDict = dict[str, Any]


@runtime_checkable
class UsageRepository(Protocol):
    """Protocol for usage data readers (SQLite, JSONL, etc.)."""

    def fetch_summary(self, *, days: int | None = None) -> RowDict: ...
    def fetch_summary_steps(self, *, days: int | None = None) -> RowDict: ...
    def fetch_summary_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> RowDict: ...
    def fetch_summary_for_day_steps(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> RowDict | None: ...
    def fetch_session_count(self, *, days: int | None = None) -> int: ...
    def fetch_daily(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_daily_steps(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_daily_session_counts(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> dict[str, int]: ...
    def fetch_model_usage(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_model_usage_detail(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_model_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_model_detail(
        self, *, model_id: str, days: int | None = None
    ) -> RowDict | None: ...
    def fetch_daily_model_detail(
        self, *, model_id: str, days: int | None = None
    ) -> list[RowDict]: ...
    def fetch_daily_model_usage(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_project_usage_detail(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_project_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_project_model_usage(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_project_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_session_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_project_session_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[RowDict]: ...
    def fetch_project_session_model_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[RowDict]: ...
    def fetch_active_session(
        self, *, session_id: str | None = None
    ) -> RowDict | None: ...
    def fetch_sessions_summary(
        self,
        *,
        limit: int = 20,
        include_archived: bool = False,
        min_time_updated_ms: int | None = None,
    ) -> list[RowDict]: ...
    def fetch_live_summary_messages(
        self, *, since_ms: int, session_id: str | None = None
    ) -> RowDict: ...
    def fetch_live_summary_steps(
        self, *, since_ms: int, session_id: str | None = None
    ) -> RowDict: ...
    def fetch_live_model_usage(
        self, *, since_ms: int, limit: int = 5, session_id: str | None = None
    ) -> list[RowDict]: ...
    def fetch_live_tool_usage(
        self, *, since_ms: int, limit: int = 8, session_id: str | None = None
    ) -> list[RowDict]: ...
    def resolve_token_source(
        self,
        *,
        days: int | None,
        token_source: Literal["auto", "message", "steps"],
    ) -> Literal["message", "steps"]: ...
    def resolve_session_count_source(
        self,
        *,
        days: int | None,
        session_count_source: Literal["auto", "activity", "session"],
    ) -> Literal["activity", "session"]: ...


def create_repository(kind: str, path: Path) -> UsageRepository:
    """Factory function to create the appropriate repository."""
    if kind == "sqlite":
        from modelmeter.data.sqlite_usage_repository import SQLiteUsageRepository

        return SQLiteUsageRepository(path)
    if kind == "jsonl":
        from modelmeter.data.jsonl_usage_repository import JsonlUsageRepository

        return JsonlUsageRepository(path)
    raise ValueError(f"Unknown repository kind: {kind}")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_repository_protocol.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/data/repository.py tests/test_repository_protocol.py
git commit -m "feat: add UsageRepository Protocol and factory function"
```

---

### Task 2: Adapt SQLiteUsageRepository to return RowDict

**Files:**
- Modify: `src/modelmeter/data/sqlite_usage_repository.py`
- Test: `tests/test_repository_protocol.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/test_repository_protocol.py`:

```python
from modelmeter.data.sqlite_usage_repository import SQLiteUsageRepository
from modelmeter.data.repository import UsageRepository


def test_sqlite_repository_satisfies_protocol() -> None:
    """SQLiteUsageRepository should be a structural subtype of UsageRepository."""
    assert issubclass(SQLiteUsageRepository, UsageRepository)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_repository_protocol.py::test_sqlite_repository_satisfies_protocol -v`
Expected: FAIL — `sqlite3.Row` return types don't match `dict[str, Any]`

- [ ] **Step 3: Add `_to_dict` helper and wrap returns in SQLiteUsageRepository**

Add a private static method to `SQLiteUsageRepository`:

```python
@staticmethod
def _to_dict(row: sqlite3.Row) -> dict[str, Any]:
    """Convert sqlite3.Row to plain dict for Protocol compatibility."""
    return dict(row)

@staticmethod
def _to_dict_list(rows: list[sqlite3.Row]) -> list[dict[str, Any]]:
    """Convert list of sqlite3.Row to list of dicts."""
    return [dict(row) for row in rows]

@staticmethod
def _to_dict_optional(row: sqlite3.Row | None) -> dict[str, Any] | None:
    """Convert optional sqlite3.Row to optional dict."""
    return dict(row) if row is not None else None
```

Then update every `return` statement in the 27 fetch methods:
- Single-row methods: `return self._to_dict(row)` instead of `return row`
- List methods: `return self._to_dict_list(result)` instead of `return result`
- Optional methods: `return self._to_dict_optional(row)` instead of `return row`
- Update return type annotations from `sqlite3.Row` to `dict[str, Any]`, `list[sqlite3.Row]` to `list[dict[str, Any]]`, `sqlite3.Row | None` to `dict[str, Any] | None`
- Keep internal caching unchanged (cache the dicts)

**Important:** Also update the `_cache` usage: cached values should be dicts, not Rows. Since `_to_dict` is called before caching, cached values are already dicts after this change.

- [ ] **Step 4: Run test to verify it passes**

Run: `uv run pytest tests/test_repository_protocol.py -v`
Expected: PASS

- [ ] **Step 5: Run full test suite to check for regressions**

Run: `uv run pytest tests/ -v`
Expected: All tests pass (the dict conversion is compatible with existing code that calls `dict(row)`)

- [ ] **Step 6: Run type checker**

Run: `uv run pyright src/modelmeter/data/sqlite_usage_repository.py src/modelmeter/data/repository.py`
Expected: No errors

- [ ] **Step 7: Commit**

```bash
git add src/modelmeter/data/sqlite_usage_repository.py tests/test_repository_protocol.py
git commit -m "refactor: adapt SQLiteUsageRepository to return RowDict for Protocol compat"
```

---

### Task 3: Generalize _token_usage_from_row in analytics.py and live.py

**Files:**
- Modify: `src/modelmeter/core/analytics.py:38-45`
- Modify: `src/modelmeter/core/live.py:51-58`

- [ ] **Step 1: Update analytics.py**

Change `_token_usage_from_row` from:
```python
def _token_usage_from_row(row: sqlite3.Row) -> TokenUsage:
    mapping = dict(row)  # sqlite3.Row behaves like a mapping
```

To:
```python
def _token_usage_from_row(row: dict[str, Any]) -> TokenUsage:
    mapping = row
```

Remove the `import sqlite3` if it's no longer used elsewhere in the file (check first — it may be used in catch blocks like `except sqlite3.Error`).

- [ ] **Step 2: Update live.py**

Same change in `live.py:51-58`:
```python
def _token_usage_from_row(row: dict[str, Any]) -> TokenUsage:
    mapping = row
```

Also update the `summary_row` type annotation at line 93 from `sqlite3.Row` to `dict[str, Any]`.

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_api.py tests/test_federation.py -v`
Expected: All pass

- [ ] **Step 4: Run type checker on modified files**

Run: `uv run pyright src/modelmeter/core/analytics.py src/modelmeter/core/live.py`
Expected: No errors

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/core/analytics.py src/modelmeter/core/live.py
git commit -m "refactor: generalize _token_usage_from_row to accept dict instead of sqlite3.Row"
```

---

### Task 4: Update data module __init__.py exports

**Files:**
- Modify: `src/modelmeter/data/__init__.py` (if it exists)

- [ ] **Step 1: Check if data/__init__.py exists**

If it exists, add exports for the new module:
```python
from modelmeter.data.repository import RowDict, UsageRepository, create_repository
```

If it doesn't exist, skip this task.

- [ ] **Step 2: Run format and lint**

Run: `uv run ruff format src/modelmeter/data/ && uv run ruff check src/modelmeter/data/`
Expected: Clean

- [ ] **Step 3: Commit if changes were made**

```bash
git add src/modelmeter/data/
git commit -m "chore: export repository Protocol from data module"
```

---

## Verification

After all tasks:

```bash
uv run pytest tests/ -v
uv run pyright
uv run ruff check
```

All must pass. The factory's `"jsonl"` branch will raise `ImportError` until Plan 28 creates `JsonlUsageRepository` — this is expected and the factory is not called with `"jsonl"` yet.
