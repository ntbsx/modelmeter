# 28. Claude Code JSONL Reader

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build `JsonlUsageRepository` that reads Claude Code session JSONL files from `~/.claude/projects/` and implements the `UsageRepository` Protocol from Plan 27.

**Architecture:** A JSONL parser builds an in-memory `SessionIndex` from Claude Code session files. The index caches parsed data keyed by file mtimes. Each Protocol method queries the index to produce aggregated `RowDict` results matching the same column contract as `SQLiteUsageRepository`.

**Tech Stack:** Python, pathlib, json, hashlib, datetime

**Dependencies:** Plan 27 (repository Protocol)

---

### Task 1: Create test fixtures for Claude Code JSONL data

**Files:**
- Create: `tests/fixtures/claudecode/`
- Create: `tests/fixtures/claudecode/-Users-test-projs-myproject/session-001.jsonl`
- Create: `tests/fixtures/claudecode/-Users-test-projs-myproject/session-002.jsonl`
- Create: `tests/fixtures/claudecode/-Users-test-projs-other/session-003.jsonl`
- Create: `tests/fixtures/claudecode/-Users-test-projs-myproject/session-004/subagents/agent-sub1.jsonl`
- Create: `tests/fixtures/claudecode/-Users-test-projs-myproject/session-004.jsonl`

- [ ] **Step 1: Create fixture directory structure**

```bash
mkdir -p tests/fixtures/claudecode/-Users-test-projs-myproject/session-004/subagents
mkdir -p tests/fixtures/claudecode/-Users-test-projs-other
```

- [ ] **Step 2: Create session-001.jsonl — minimal session with 2 assistant messages**

Each line is a valid JSON object. Include:
- A `user` record (no token data)
- An `assistant` record with `stop_reason: "end_turn"` and `usage` (100 input, 50 output, 20 cache read, 10 cache write), model `claude-sonnet-4-6`, timestamp `2026-03-20T10:00:00.000Z`
- A second `assistant` record with `stop_reason: "end_turn"`, model `claude-sonnet-4-6`, similar usage
- A `custom-title` record with title `"test session one"`
- All records have `sessionId: "session-001"`, `cwd: "/Users/test/projs/myproject"`

- [ ] **Step 3: Create session-002.jsonl — session with streaming duplicates**

Include:
- An `assistant` record with `stop_reason: null` (intermediate — should be SKIPPED)
- An `assistant` record with `stop_reason: "end_turn"` (final — should be COUNTED)
- Both for model `claude-opus-4-6`
- `sessionId: "session-002"`, `cwd: "/Users/test/projs/myproject"`, timestamp `2026-03-21T14:00:00.000Z`

- [ ] **Step 4: Create session-003.jsonl — different project**

- One `assistant` record, model `claude-sonnet-4-6`, `stop_reason: "end_turn"`
- `sessionId: "session-003"`, `cwd: "/Users/test/projs/other"`, timestamp `2026-03-20T12:00:00.000Z`

- [ ] **Step 5: Create session-004.jsonl and subagent — session with subagent**

Main session:
- One `assistant` record, `stop_reason: "end_turn"`, 200 input tokens
- `sessionId: "session-004"`, `cwd: "/Users/test/projs/myproject"`

Subagent (`agent-sub1.jsonl`):
- One `assistant` record with `isSidechain: true`, `stop_reason: "end_turn"`, 50 input tokens

- [ ] **Step 6: Commit fixtures**

```bash
git add tests/fixtures/claudecode/
git commit -m "test: add Claude Code JSONL test fixtures"
```

---

### Task 2: Implement JSONL parser core (record parsing and session indexing)

**Files:**
- Create: `src/modelmeter/data/jsonl_usage_repository.py`
- Test: `tests/test_jsonl_reader.py`

- [ ] **Step 1: Write failing tests for JSONL parsing**

```python
# tests/test_jsonl_reader.py
"""Tests for Claude Code JSONL data reader."""

from pathlib import Path

import pytest

from modelmeter.data.jsonl_usage_repository import JsonlUsageRepository

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "claudecode"


@pytest.fixture
def repo() -> JsonlUsageRepository:
    return JsonlUsageRepository(FIXTURES_DIR)


def test_repo_builds_index(repo: JsonlUsageRepository) -> None:
    """Repository should discover and parse session JSONL files."""
    index = repo._ensure_index()
    assert len(index.sessions) >= 4


def test_repo_skips_streaming_duplicates(repo: JsonlUsageRepository) -> None:
    """Records with stop_reason=null should not be counted."""
    index = repo._ensure_index()
    session_002 = next(s for s in index.sessions if s.session_id == "session-002")
    # Only the final record (stop_reason="end_turn") should be counted
    assert len(session_002.interactions) == 1


def test_repo_reads_cwd_for_project_path(repo: JsonlUsageRepository) -> None:
    """Project path should come from cwd field, not directory name."""
    index = repo._ensure_index()
    session_001 = next(s for s in index.sessions if s.session_id == "session-001")
    assert session_001.project_path == "/Users/test/projs/myproject"


def test_repo_aggregates_subagent_tokens(repo: JsonlUsageRepository) -> None:
    """Subagent tokens should be aggregated into parent session."""
    index = repo._ensure_index()
    session_004 = next(s for s in index.sessions if s.session_id == "session-004")
    # Should include both main session and subagent interactions
    assert len(session_004.interactions) >= 2
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `uv run pytest tests/test_jsonl_reader.py -v`
Expected: FAIL — `ModuleNotFoundError`

- [ ] **Step 3: Implement JsonlUsageRepository core**

Create `src/modelmeter/data/jsonl_usage_repository.py` with:

1. **Data classes** for the in-memory index:
   - `Interaction(model_id, provider_id, input_tokens, output_tokens, cache_read, cache_write, timestamp_ms, session_id)`
   - `SessionData(session_id, title, project_id, project_name, project_path, cwd, time_created_ms, time_updated_ms, interactions, model_count, message_count)`
   - `SessionIndex(sessions, project_map)` — `project_map` maps project_id to project metadata

2. **Parsing logic:**
   - `_scan_jsonl_files()` — find all `.jsonl` files in `projects/` subdirectories, including subagent files
   - `_parse_session_file(path)` → list of parsed records
   - `_build_session_from_records(records, subagent_records)` → `SessionData`
   - Filter: only count `type=assistant` records where `message.stop_reason is not None`
   - Read `cwd` from first record for project path
   - Read `sessionId` from records or derive from filename
   - Read title from `type=custom-title` or `type=agent-name` records
   - Generate `project_id` as `hashlib.md5(cwd.encode()).hexdigest()[:16]`
   - Assign `provider_id` via `provider_from_model_id` from `providers.py`

3. **Mtime-based caching:**
   - `_scan_file_mtimes()` → `dict[Path, float]`
   - `_ensure_index()` — rebuild if mtimes changed

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_jsonl_reader.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/data/jsonl_usage_repository.py tests/test_jsonl_reader.py
git commit -m "feat: implement JSONL parser core with session indexing"
```

---

### Task 3: Implement Protocol methods — summary, daily, session count

**Files:**
- Modify: `src/modelmeter/data/jsonl_usage_repository.py`
- Test: `tests/test_jsonl_reader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_fetch_summary(repo: JsonlUsageRepository) -> None:
    """fetch_summary should aggregate all token usage."""
    row = repo.fetch_summary()
    assert row["input_tokens"] > 0
    assert row["output_tokens"] > 0
    assert row["total_sessions"] >= 4


def test_fetch_summary_with_days_filter(repo: JsonlUsageRepository) -> None:
    """fetch_summary with days filter should only include recent data."""
    row = repo.fetch_summary(days=1)
    # Fixtures have dates in the past, so this may return 0
    assert "input_tokens" in row
    assert "total_sessions" in row


def test_fetch_daily(repo: JsonlUsageRepository) -> None:
    """fetch_daily should return per-day aggregates."""
    rows = repo.fetch_daily()
    assert len(rows) > 0
    for row in rows:
        assert "day" in row
        assert "input_tokens" in row
        assert "total_sessions" in row


def test_fetch_session_count(repo: JsonlUsageRepository) -> None:
    """fetch_session_count should return total sessions."""
    count = repo.fetch_session_count()
    assert count >= 4
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement summary, daily, and session_count methods**

Add these aggregation methods to `JsonlUsageRepository`:

- `fetch_summary(days)` — filter interactions by days cutoff, aggregate tokens, count distinct sessions
- `fetch_summary_steps(days)` — for JSONL, equivalent to `fetch_summary` (no steps table distinction)
- `fetch_summary_for_day(day, timezone_offset_minutes)` — filter to single day
- `fetch_summary_for_day_steps(day, timezone_offset_minutes)` — equivalent to `fetch_summary_for_day`
- `fetch_session_count(days)` — count distinct session IDs within time window
- `fetch_daily(days, timezone_offset_minutes)` — group by day, return list of dicts
- `fetch_daily_steps(days, timezone_offset_minutes)` — equivalent to `fetch_daily`
- `fetch_daily_session_counts(days, timezone_offset_minutes)` — sessions per day

For `resolve_token_source` and `resolve_session_count_source`: always return `"message"` and `"activity"` respectively (Claude Code has no steps/session table distinction).

Helper: `_filter_interactions(days)` — returns interactions within time window.

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/data/jsonl_usage_repository.py tests/test_jsonl_reader.py
git commit -m "feat: implement summary, daily, and session count methods for JSONL reader"
```

---

### Task 4: Implement Protocol methods — model usage

**Files:**
- Modify: `src/modelmeter/data/jsonl_usage_repository.py`
- Test: `tests/test_jsonl_reader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_fetch_model_usage(repo: JsonlUsageRepository) -> None:
    """fetch_model_usage should group by model_id."""
    rows = repo.fetch_model_usage()
    assert len(rows) > 0
    model_ids = [r["model_id"] for r in rows]
    assert "claude-sonnet-4-6" in model_ids


def test_fetch_model_usage_detail(repo: JsonlUsageRepository) -> None:
    """fetch_model_usage_detail should include interaction/session counts."""
    rows = repo.fetch_model_usage_detail()
    assert len(rows) > 0
    for row in rows:
        assert "total_interactions" in row
        assert "total_sessions" in row
        assert "provider_id" in row


def test_fetch_model_detail(repo: JsonlUsageRepository) -> None:
    """fetch_model_detail should return detail for specific model."""
    row = repo.fetch_model_detail(model_id="claude-sonnet-4-6")
    assert row is not None
    assert row["total_interactions"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement model usage methods**

- `fetch_model_usage(days)` — group by model_id, aggregate tokens
- `fetch_model_usage_detail(days)` — group by (model_id, provider_id), include counts
- `fetch_model_usage_detail_for_day(day, tz)` — same for single day
- `fetch_model_detail(model_id, days)` — aggregate for specific model
- `fetch_daily_model_detail(model_id, days)` — daily breakdown for one model
- `fetch_daily_model_usage(days, tz)` — group by (day, model_id, provider_id)

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/data/jsonl_usage_repository.py tests/test_jsonl_reader.py
git commit -m "feat: implement model usage methods for JSONL reader"
```

---

### Task 5: Implement Protocol methods — project and session usage

**Files:**
- Modify: `src/modelmeter/data/jsonl_usage_repository.py`
- Test: `tests/test_jsonl_reader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_fetch_project_usage_detail(repo: JsonlUsageRepository) -> None:
    """fetch_project_usage_detail should group by project."""
    rows = repo.fetch_project_usage_detail()
    assert len(rows) >= 2  # Two projects in fixtures
    for row in rows:
        assert "project_id" in row
        assert "project_name" in row
        assert "project_path" in row


def test_fetch_project_session_usage(repo: JsonlUsageRepository) -> None:
    """fetch_project_session_usage should return sessions for a project."""
    # Get any project_id from the index
    projects = repo.fetch_project_usage_detail()
    assert len(projects) > 0
    project_id = projects[0]["project_id"]
    sessions = repo.fetch_project_session_usage(project_id=project_id)
    assert len(sessions) > 0


def test_fetch_sessions_summary(repo: JsonlUsageRepository) -> None:
    """fetch_sessions_summary should return recent sessions."""
    sessions = repo.fetch_sessions_summary(limit=10)
    assert len(sessions) > 0
    for s in sessions:
        assert "session_id" in s
        assert "time_created" in s
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement project and session methods**

- `fetch_project_usage_detail(days)` — group by project
- `fetch_project_usage_detail_for_day(day, tz)` — same for single day
- `fetch_project_model_usage(days)` — group by (project, model)
- `fetch_project_model_usage_for_day(day, tz)` — same for single day
- `fetch_session_model_usage_for_day(day, tz)` — group by (session, model) with started_at_ms
- `fetch_project_session_usage(project_id, days)` — sessions within one project
- `fetch_project_session_model_usage(project_id, days)` — model breakdown per session
- `fetch_active_session(session_id)` — most recently updated session
- `fetch_sessions_summary(limit, include_archived, min_time_updated_ms)` — recent sessions with metadata

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/data/jsonl_usage_repository.py tests/test_jsonl_reader.py
git commit -m "feat: implement project and session methods for JSONL reader"
```

---

### Task 6: Implement Protocol methods — live monitoring

**Files:**
- Modify: `src/modelmeter/data/jsonl_usage_repository.py`
- Test: `tests/test_jsonl_reader.py`

- [ ] **Step 1: Write failing tests**

```python
def test_fetch_live_summary(repo: JsonlUsageRepository) -> None:
    """fetch_live_summary_messages should return recent usage."""
    # Use a very old since_ms to capture all fixture data
    row = repo.fetch_live_summary_messages(since_ms=0)
    assert "total_interactions" in row
    assert "input_tokens" in row


def test_fetch_live_model_usage(repo: JsonlUsageRepository) -> None:
    """fetch_live_model_usage should return recent model usage."""
    rows = repo.fetch_live_model_usage(since_ms=0, limit=5)
    assert len(rows) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Implement live methods**

- `fetch_live_summary_messages(since_ms, session_id)` — aggregate tokens since timestamp
- `fetch_live_summary_steps(since_ms, session_id)` — equivalent (no steps distinction)
- `fetch_live_model_usage(since_ms, limit, session_id)` — top models since timestamp
- `fetch_live_tool_usage(since_ms, limit, session_id)` — return empty list (Claude Code JSONL doesn't have tool usage in the same format; future enhancement)

- [ ] **Step 4: Run tests to verify they pass**

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/data/jsonl_usage_repository.py tests/test_jsonl_reader.py
git commit -m "feat: implement live monitoring methods for JSONL reader"
```

---

### Task 7: Verify Protocol compliance and run full suite

**Files:**
- Modify: `tests/test_repository_protocol.py`

- [ ] **Step 1: Add Protocol compliance test for JsonlUsageRepository**

```python
from modelmeter.data.jsonl_usage_repository import JsonlUsageRepository


def test_jsonl_repository_satisfies_protocol() -> None:
    """JsonlUsageRepository should be a structural subtype of UsageRepository."""
    assert issubclass(JsonlUsageRepository, UsageRepository)
```

- [ ] **Step 2: Run Protocol compliance tests**

Run: `uv run pytest tests/test_repository_protocol.py -v`
Expected: All pass

- [ ] **Step 3: Run type checker**

Run: `uv run pyright src/modelmeter/data/jsonl_usage_repository.py`
Expected: No errors

- [ ] **Step 4: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All pass

- [ ] **Step 5: Commit**

```bash
git add tests/test_repository_protocol.py
git commit -m "test: verify JsonlUsageRepository satisfies UsageRepository Protocol"
```

---

## Verification

After all tasks:

```bash
uv run pytest tests/test_jsonl_reader.py tests/test_repository_protocol.py -v
uv run pyright src/modelmeter/data/
uv run ruff check src/modelmeter/data/
```
