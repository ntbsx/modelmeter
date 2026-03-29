# 30. Analytics Multi-Repo and Federation Integration

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Refactor the analytics layer so `scope=local` queries all detected local repositories (OpenCode + Claude Code) and merges results. Extend federation to support JSONL sources.

**Architecture:** Add `_resolve_local_repositories()` that returns a list of `(source_id, UsageRepository)` tuples. Refactor each analytics function's local branch to iterate and merge. Add `"jsonl"` branch to federation dispatch.

**Tech Stack:** Python, existing merge functions from `federation.py`

**Dependencies:** Plans 27, 28, 29

---

### Task 1: Add _resolve_local_repositories helper

**Files:**
- Modify: `src/modelmeter/core/analytics.py`
- Test: `tests/test_multi_agent_federation.py`

- [ ] **Step 1: Write failing test**

```python
# tests/test_multi_agent_federation.py
"""Tests for multi-agent local source resolution and merging."""

from pathlib import Path
from unittest.mock import patch

from modelmeter.config.settings import AppSettings


def test_resolve_local_repositories_opencode_only(tmp_path: Path) -> None:
    """When only OpenCode is available, return one repository."""
    from modelmeter.core.analytics import _resolve_local_repositories

    # Create a fake SQLite db
    db_path = tmp_path / "opencode.db"
    db_path.touch()

    settings = AppSettings(
        opencode_data_dir=tmp_path,
        opencode_db_path=db_path,
        claudecode_enabled=False,
    )

    with patch("modelmeter.core.analytics._resolve_sqlite_path", return_value=db_path):
        repos = _resolve_local_repositories(settings)
    assert len(repos) == 1
    assert repos[0][0] == "local-opencode"


def test_resolve_local_repositories_claudecode_only(tmp_path: Path) -> None:
    """When only Claude Code is available, return one repository."""
    from modelmeter.core.analytics import _resolve_local_repositories

    # Create a fake Claude Code structure
    projects_dir = tmp_path / "claudecode" / "projects" / "-test-proj"
    projects_dir.mkdir(parents=True)
    (projects_dir / "session.jsonl").write_text('{"type":"user"}\n')

    settings = AppSettings(
        opencode_data_dir=tmp_path / "nonexistent",
        claudecode_data_dir=tmp_path / "claudecode",
        claudecode_enabled=True,
    )

    repos = _resolve_local_repositories(settings)
    assert len(repos) == 1
    assert repos[0][0] == "local-claudecode"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_multi_agent_federation.py -v`

- [ ] **Step 3: Implement _resolve_local_repositories**

Add to `src/modelmeter/core/analytics.py`:

```python
from modelmeter.data.repository import UsageRepository, create_repository


def _resolve_local_repositories(
    settings: AppSettings,
    db_path_override: Path | None = None,
) -> list[tuple[str, UsageRepository]]:
    """Resolve all available local data repositories."""
    repos: list[tuple[str, UsageRepository]] = []

    # Try OpenCode SQLite
    try:
        sqlite_path = _resolve_sqlite_path(settings, db_path_override)
        repos.append(("local-opencode", create_repository("sqlite", sqlite_path)))
    except RuntimeError:
        pass  # OpenCode not available

    # Try Claude Code JSONL
    if settings.claudecode_enabled:
        projects_dir = settings.claudecode_data_dir / "projects"
        if projects_dir.exists() and any(projects_dir.rglob("*.jsonl")):
            repos.append(
                ("local-claudecode", create_repository("jsonl", settings.claudecode_data_dir))
            )

    return repos
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/core/analytics.py tests/test_multi_agent_federation.py
git commit -m "feat: add _resolve_local_repositories for multi-agent local sources"
```

---

### Task 2: Refactor get_summary for multi-repo local scope

**Files:**
- Modify: `src/modelmeter/core/analytics.py` (get_summary function)
- Test: `tests/test_multi_agent_federation.py`

- [ ] **Step 1: Write failing test**

```python
def test_get_summary_merges_local_sources(tmp_path: Path) -> None:
    """get_summary with scope=local should merge data from both agents."""
    # This test uses mock repositories to verify merge logic
    # Details depend on how the mock is structured
    pass  # Placeholder — implement with appropriate mocking
```

- [ ] **Step 2: Refactor get_summary local branch**

Replace the current local path:
```python
# BEFORE (lines ~218-273):
sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
repository = SQLiteUsageRepository(sqlite_db_path)
...
```

With multi-repo logic:
```python
# AFTER:
local_repos = _resolve_local_repositories(settings, db_path_override)
if not local_repos:
    raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

if len(local_repos) == 1:
    # Single source — use directly (preserves current behavior)
    source_id, repository = local_repos[0]
    # ... existing logic unchanged ...
    sources_considered = [source_id]
    sources_succeeded = [source_id]
else:
    # Multiple sources — query each and merge
    from modelmeter.core.federation import merge_token_usage
    merged_usage = TokenUsage(input_tokens=0, output_tokens=0, cache_read_tokens=0, cache_write_tokens=0)
    merged_sessions = 0
    merged_cost: float | None = None
    sources_considered = []
    sources_succeeded = []
    sources_failed_list: list[dict[str, str]] = []

    for source_id, repo in local_repos:
        try:
            # Query this repo
            row = repo.fetch_summary(days=days)
            usage = _token_usage_from_row(row)
            sessions = repo.fetch_session_count(days=days)
            model_rows = repo.fetch_model_usage(days=days)
            # Calculate cost
            repo_cost = _calculate_total_cost(model_rows, pricing_book)
            # Merge
            merged_usage = merge_token_usage(merged_usage, usage)
            merged_sessions += sessions
            if repo_cost is not None:
                merged_cost = (merged_cost or 0.0) + repo_cost
            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed_list.append({"source_id": source_id, "error": str(exc)})
        sources_considered.append(source_id)

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    return SummaryResponse(
        usage=merged_usage,
        total_sessions=merged_sessions,
        window_days=days,
        cost_usd=round(merged_cost, 8) if merged_cost is not None else None,
        pricing_source=pricing_source,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed_list,
    )
```

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_api.py tests/test_multi_agent_federation.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/modelmeter/core/analytics.py tests/test_multi_agent_federation.py
git commit -m "refactor: get_summary supports multi-repo local scope"
```

---

### Task 3: Refactor remaining analytics functions for multi-repo

**Files:**
- Modify: `src/modelmeter/core/analytics.py`

Apply the same multi-repo pattern to:

- [ ] **Step 1: Refactor get_daily**
- [ ] **Step 2: Refactor get_models**
- [ ] **Step 3: Refactor get_providers**
- [ ] **Step 4: Refactor get_projects**
- [ ] **Step 5: Refactor get_project_detail**
- [ ] **Step 6: Refactor get_date_insights**

For each function:
1. Replace `_resolve_sqlite_path` + `SQLiteUsageRepository()` with `_resolve_local_repositories()`
2. Single-source path: use repository directly (unchanged logic)
3. Multi-source path: query each repo, merge using existing merge functions, handle errors per-source

**Note:** `get_date_insights` and `get_model_detail` currently raise `NotImplementedError` for non-local scope. For multi-local, they need the same pattern.

- [ ] **Step 7: Run full test suite**

Run: `uv run pytest tests/ -v`
Expected: All pass

- [ ] **Step 8: Commit**

```bash
git add src/modelmeter/core/analytics.py
git commit -m "refactor: all analytics functions support multi-repo local scope"
```

---

### Task 4: Add JSONL branch to federation dispatch

**Files:**
- Modify: `src/modelmeter/core/federation.py`
- Test: `tests/test_federation.py`

- [ ] **Step 1: Write failing test**

```python
def test_federation_supports_jsonl_kind() -> None:
    """Federation should handle source.kind='jsonl'."""
    # Test that execute_summary_federated can dispatch to a jsonl source
    pass  # Implement with mock JSONL source
```

- [ ] **Step 2: Add jsonl branch to federation functions**

In each `execute_*_federated` function, add handling for `source.kind == "jsonl"`:

```python
elif source.kind == "jsonl":
    assert source.db_path is not None
    repo = create_repository("jsonl", source.db_path)
    # Query repo and build response model
    ...
```

The pattern mirrors the existing `sqlite` branch but uses the factory.

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_federation.py -v`

- [ ] **Step 4: Run type checker**

Run: `uv run pyright src/modelmeter/core/federation.py`

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/core/federation.py tests/test_federation.py
git commit -m "feat: add JSONL source support to federation dispatch"
```

---

## Verification

```bash
uv run pytest tests/ -v
uv run pyright src/modelmeter/core/analytics.py src/modelmeter/core/federation.py
make release-check
```
