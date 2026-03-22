# 29. Auto-Detection, Settings, Doctor, and Agent Identity

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Claude Code auto-detection, `agent` field to sources, multi-agent doctor report, and settings for Claude Code data directory.

**Architecture:** Extend `AppSettings` with Claude Code config. Add `agent` field and `"jsonl"` kind to source models. Extend doctor to detect both OpenCode and Claude Code. Add health check for JSONL sources.

**Tech Stack:** Python, Pydantic, Pydantic-Settings

**Dependencies:** Plan 27, Plan 28

---

### Task 1: Extend AppSettings with Claude Code settings

**Files:**
- Modify: `src/modelmeter/config/settings.py`
- Test: `tests/test_settings.py`

- [ ] **Step 1: Write failing test**

```python
def test_claudecode_settings_defaults() -> None:
    """Settings should have Claude Code defaults."""
    from modelmeter.config.settings import AppSettings

    settings = AppSettings()
    assert hasattr(settings, "claudecode_data_dir")
    assert hasattr(settings, "claudecode_enabled")
    assert settings.claudecode_enabled is True
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest tests/test_settings.py::test_claudecode_settings_defaults -v`

- [ ] **Step 3: Add settings**

Add to `AppSettings` in `src/modelmeter/config/settings.py`:

```python
claudecode_data_dir: Path = Field(default=Path.home() / ".claude")
claudecode_enabled: bool = True
```

- [ ] **Step 4: Run test to verify it passes**

- [ ] **Step 5: Commit**

```bash
git add src/modelmeter/config/settings.py tests/test_settings.py
git commit -m "feat: add Claude Code data directory settings"
```

---

### Task 2: Extend source models with agent field and jsonl kind

**Files:**
- Modify: `src/modelmeter/core/sources.py`
- Test: `tests/test_sources.py`

- [ ] **Step 1: Write failing tests**

```python
def test_data_source_config_jsonl_kind() -> None:
    """DataSourceConfig should accept kind='jsonl'."""
    from modelmeter.core.sources import DataSourceConfig
    from pathlib import Path

    source = DataSourceConfig(
        source_id="local-claudecode",
        kind="jsonl",
        db_path=Path("/tmp/test"),
    )
    assert source.kind == "jsonl"


def test_data_source_config_agent_field() -> None:
    """DataSourceConfig should have an optional agent field."""
    from modelmeter.core.sources import DataSourceConfig
    from pathlib import Path

    source = DataSourceConfig(
        source_id="local-opencode",
        kind="sqlite",
        db_path=Path("/tmp/test.db"),
        agent="opencode",
    )
    assert source.agent == "opencode"
```

- [ ] **Step 2: Run tests to verify they fail**

- [ ] **Step 3: Update source models**

In `src/modelmeter/core/sources.py`:

1. Expand `DataSourceConfig.kind`:
   ```python
   kind: Literal["sqlite", "http", "jsonl"]
   ```

2. Add `agent` field:
   ```python
   agent: Literal["opencode", "claudecode"] | None = None
   ```

3. Update `validate_kind_fields` model validator to handle `"jsonl"`:
   ```python
   if self.kind == "sqlite":
       if self.db_path is None:
           raise ValueError("sqlite source requires db_path")
   elif self.kind == "jsonl":
       if self.db_path is None:
           raise ValueError("jsonl source requires db_path")
   elif self.base_url is None:
       raise ValueError("http source requires base_url")
   ```

4. Expand `SourceFailure.kind`:
   ```python
   kind: Literal["sqlite", "http", "jsonl"]
   ```

5. Expand `DataSourcePublic.kind`, `SourceHealth.kind`:
   ```python
   kind: Literal["sqlite", "http", "jsonl"]
   ```

6. Add `agent` to `DataSourcePublic`:
   ```python
   agent: Literal["opencode", "claudecode"] | None = None
   ```

7. Update `to_public_registry` to include `agent`:
   ```python
   agent=source.agent,
   ```

8. Add JSONL health check in `check_source_health`:
   ```python
   if source.kind == "sqlite":
       return _check_sqlite_source(source)
   if source.kind == "jsonl":
       return _check_jsonl_source(source)
   return _check_http_source(source, timeout_seconds=settings.source_http_timeout_seconds)
   ```

9. Implement `_check_jsonl_source`:
   ```python
   def _check_jsonl_source(source: DataSourceConfig) -> SourceHealth:
       assert source.db_path is not None
       projects_dir = source.db_path / "projects"
       if not projects_dir.exists():
           return SourceHealth(
               source_id=source.source_id,
               kind=source.kind,
               is_reachable=False,
               error=f"Projects directory not found at {projects_dir}",
           )
       jsonl_count = sum(1 for _ in projects_dir.rglob("*.jsonl"))
       return SourceHealth(
           source_id=source.source_id,
           kind=source.kind,
           is_reachable=True,
           detail=f"{jsonl_count} session files",
       )
   ```

- [ ] **Step 4: Run tests to verify they pass**

Run: `uv run pytest tests/test_sources.py -v`

- [ ] **Step 5: Run type checker**

Run: `uv run pyright src/modelmeter/core/sources.py`

- [ ] **Step 6: Commit**

```bash
git add src/modelmeter/core/sources.py tests/test_sources.py
git commit -m "feat: add jsonl kind and agent field to source models"
```

---

### Task 3: Extend doctor with multi-agent detection

**Files:**
- Modify: `src/modelmeter/core/doctor.py`
- Test: `tests/test_doctor.py` (create or extend)

- [ ] **Step 1: Write failing test**

```python
def test_doctor_report_has_detected_sources() -> None:
    """DoctorReport should include detected_sources list."""
    from modelmeter.core.doctor import DoctorReport

    report = DoctorReport(
        app_name="test",
        app_version="1.0",
        opencode_data_dir="/tmp",
        selected_source="none",
        sqlite=...,  # minimal SQLiteDiagnostics
        legacy=...,  # minimal LegacyDiagnostics
    )
    assert hasattr(report, "detected_sources")
    assert isinstance(report.detected_sources, list)
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Add DetectedSource model and extend DoctorReport**

In `src/modelmeter/core/doctor.py`:

```python
class DetectedSource(BaseModel):
    """Detected local data source."""

    kind: Literal["sqlite", "jsonl"]
    agent: Literal["opencode", "claudecode"]
    status: Literal["ok", "error"]
    path: str
    details: str | None = None


class DoctorReport(BaseModel):
    """Top-level health diagnostics payload."""

    app_name: str
    app_version: str
    opencode_data_dir: str
    selected_source: str  # Keep for backward compat
    sqlite: SQLiteDiagnostics
    legacy: LegacyDiagnostics
    detected_sources: list[DetectedSource] = Field(default_factory=list)
```

- [ ] **Step 4: Add Claude Code detection to generate_doctor_report**

Add a `_inspect_claudecode(data_dir: Path)` function:

```python
def _inspect_claudecode(data_dir: Path) -> DetectedSource | None:
    """Check for Claude Code JSONL data."""
    projects_dir = data_dir / "projects"
    if not projects_dir.exists():
        return None

    project_count = sum(1 for d in projects_dir.iterdir() if d.is_dir())
    session_count = sum(1 for _ in projects_dir.rglob("*.jsonl"))

    if session_count == 0:
        return None

    return DetectedSource(
        kind="jsonl",
        agent="claudecode",
        status="ok",
        path=str(data_dir),
        details=f"{project_count} projects, {session_count} sessions",
    )
```

Update `generate_doctor_report` to accept `settings` (which now has `claudecode_data_dir`):
- After existing OpenCode detection, call `_inspect_claudecode(settings.claudecode_data_dir)`
- Build `detected_sources` list from both detections
- If OpenCode SQLite is healthy: add `DetectedSource(kind="sqlite", agent="opencode", status="ok", ...)`
- Keep `selected_source` computed as before for backward compat

- [ ] **Step 5: Run tests**

Run: `uv run pytest tests/ -k "doctor" -v`

- [ ] **Step 6: Commit**

```bash
git add src/modelmeter/core/doctor.py tests/
git commit -m "feat: extend doctor with multi-agent detection and DetectedSource model"
```

---

### Task 4: Add agents_detected to health endpoint

**Files:**
- Modify: `src/modelmeter/api/app.py`
- Test: `tests/test_api.py`

- [ ] **Step 1: Write failing test**

Add to `tests/test_api.py`:

```python
def test_health_includes_agents_detected(client):
    """Health endpoint should include agents_detected field."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert "agents_detected" in data
    assert isinstance(data["agents_detected"], list)
```

- [ ] **Step 2: Run test to verify it fails**

- [ ] **Step 3: Update health endpoint**

In the `/health` endpoint handler, call `generate_doctor_report` and extract detected agents:

```python
agents_detected = [ds.agent for ds in report.detected_sources]
```

Add to response:
```python
return {
    "status": "ok",
    "app_version": settings.app_runtime_version,
    "auth_required": ...,
    "agents_detected": agents_detected,
}
```

- [ ] **Step 4: Run tests**

Run: `uv run pytest tests/test_api.py -v`

- [ ] **Step 5: Regenerate OpenAPI types**

Run: `make gen-types`

- [ ] **Step 6: Commit**

```bash
git add src/modelmeter/api/app.py tests/test_api.py web/openapi.json web/src/generated/
git commit -m "feat: add agents_detected to health endpoint"
```

---

## Verification

```bash
uv run pytest tests/test_settings.py tests/test_sources.py tests/test_api.py -v
uv run pyright src/modelmeter/config/ src/modelmeter/core/sources.py src/modelmeter/core/doctor.py
```
