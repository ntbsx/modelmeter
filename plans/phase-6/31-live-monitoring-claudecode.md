# 31. Live Monitoring for Claude Code

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Extend live monitoring to detect and display active Claude Code sessions alongside OpenCode sessions, using file mtime recency.

**Architecture:** A Claude Code session is "active" if its JSONL file was modified within the last 10 minutes. The live snapshot endpoint queries both OpenCode (SQLite) and Claude Code (JSONL) repositories. Each active session gets its own `LiveSnapshotResponse`.

**Tech Stack:** Python, pathlib, time

**Dependencies:** Plans 27-30

---

### Task 1: Add Claude Code active session detection to live.py

**Files:**
- Modify: `src/modelmeter/core/live.py`
- Test: `tests/test_live.py` (create or extend)

- [ ] **Step 1: Write failing test**

```python
def test_live_snapshot_with_claudecode(tmp_path: Path) -> None:
    """Live snapshot should work with Claude Code JSONL data."""
    # Create mock JSONL session file with recent mtime
    # Verify get_live_snapshot can use JSONL repository
    pass
```

- [ ] **Step 2: Extend get_live_snapshot for multi-agent**

In `src/modelmeter/core/live.py`:

1. Import `_resolve_local_repositories` from analytics (or duplicate the logic)
2. For `scope=local`, resolve all local repositories
3. Query each repository for live data
4. Each session gets its own snapshot — no merging needed at the live level

The existing multi-session live view (Plan 24) already handles displaying multiple sessions. The change here is that sessions can now come from different repositories.

- [ ] **Step 3: Add `get_live_sessions` function**

New function that returns a list of active sessions across all agents:

```python
def get_live_sessions(
    *,
    settings: AppSettings,
    db_path_override: Path | None = None,
) -> list[LiveActiveSession]:
    """Return all active sessions across all local agents."""
    sessions: list[LiveActiveSession] = []

    # OpenCode sessions (existing logic)
    try:
        sqlite_path = _resolve_sqlite_path(settings, db_path_override)
        repo = SQLiteUsageRepository(sqlite_path)
        active = repo.fetch_active_session()
        if active is not None:
            sessions.append(LiveActiveSession(
                session_id=str(active["id"]),
                title=active.get("title"),
                project_id=active.get("project_id"),
                project_name=active.get("project_name"),
                directory=active.get("directory"),
                last_updated_ms=int(active.get("time_updated", 0)),
                is_active=True,
            ))
    except RuntimeError:
        pass

    # Claude Code sessions (mtime-based detection)
    if settings.claudecode_enabled:
        cc_sessions = _detect_claudecode_active_sessions(settings)
        sessions.extend(cc_sessions)

    return sessions
```

- [ ] **Step 4: Implement `_detect_claudecode_active_sessions`**

```python
def _detect_claudecode_active_sessions(
    settings: AppSettings,
) -> list[LiveActiveSession]:
    """Detect active Claude Code sessions by JSONL file mtime."""
    projects_dir = settings.claudecode_data_dir / "projects"
    if not projects_dir.exists():
        return []

    now_ms = int(time.time() * 1000)
    threshold_ms = now_ms - ACTIVE_SESSION_THRESHOLD_MS
    sessions: list[LiveActiveSession] = []

    for jsonl_file in projects_dir.rglob("*.jsonl"):
        # Skip subagent files
        if "subagents" in jsonl_file.parts:
            continue

        mtime_ms = int(jsonl_file.stat().st_mtime * 1000)
        if mtime_ms < threshold_ms:
            continue

        # Parse minimal metadata from first and last lines
        # (session_id, cwd, title)
        metadata = _parse_session_metadata(jsonl_file)
        if metadata is None:
            continue

        sessions.append(LiveActiveSession(
            session_id=metadata["session_id"],
            title=metadata.get("title"),
            project_id=metadata.get("project_id"),
            project_name=metadata.get("project_name"),
            directory=metadata.get("cwd"),
            last_updated_ms=mtime_ms,
            is_active=True,
        ))

    return sessions
```

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/ -k "live" -v`

- [ ] **Step 6: Commit**

```bash
git add src/modelmeter/core/live.py tests/
git commit -m "feat: extend live monitoring to detect active Claude Code sessions"
```

---

### Task 2: Update live SSE endpoint for multi-agent sessions

**Files:**
- Modify: `src/modelmeter/api/app.py` (SSE endpoint)

- [ ] **Step 1: Update sessions list endpoint**

If there's a `/api/live/sessions` or similar endpoint, update it to use `get_live_sessions()` which now returns sessions from both agents.

- [ ] **Step 2: Update live snapshot to accept JSONL sessions**

The existing `/api/live/snapshot` endpoint takes an optional `session_id`. When a Claude Code session_id is provided, the endpoint should route to the JSONL repository instead of the SQLite one.

- [ ] **Step 3: Run tests**

Run: `uv run pytest tests/test_api.py -v`

- [ ] **Step 4: Commit**

```bash
git add src/modelmeter/api/app.py
git commit -m "feat: update live SSE endpoint for multi-agent sessions"
```

---

## Verification

```bash
uv run pytest tests/ -v
uv run pyright src/modelmeter/core/live.py
```
