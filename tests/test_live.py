from __future__ import annotations

import json
import os
import shutil
import sqlite3
import time
from pathlib import Path
from typing import Any
from unittest.mock import patch

from typer.testing import CliRunner

from modelmeter.cli.main import app
from modelmeter.config.settings import AppSettings
from modelmeter.core.live import get_live_sessions, get_live_snapshot

CLAUDECODE_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "claudecode"


class _FakeLiveRepo:
    def __init__(self, *, session_id: str, project_name: str, model_id: str) -> None:
        self.session_id = session_id
        self.project_name = project_name
        self.model_id = model_id

    def fetch_active_session(self, session_id: str | None = None) -> dict[str, Any] | None:
        if session_id is not None and session_id != self.session_id:
            return None
        return {
            "id": self.session_id,
            "title": self.project_name,
            "project_id": "p1",
            "project_name": self.project_name,
            "directory": f"/tmp/{self.project_name.lower()}",
            "time_updated": int(time.time() * 1000),
        }

    def fetch_live_summary_messages(
        self, *, since_ms: int, session_id: str | None = None
    ) -> dict[str, Any]:
        _ = since_ms
        if session_id is not None and session_id != self.session_id:
            return {
                "input_tokens": 0,
                "output_tokens": 0,
                "cache_read": 0,
                "cache_write": 0,
                "total_sessions": 0,
                "total_interactions": 0,
            }
        return {
            "input_tokens": 10,
            "output_tokens": 5,
            "cache_read": 0,
            "cache_write": 0,
            "total_sessions": 1,
            "total_interactions": 1,
        }

    def fetch_live_summary_steps(
        self, *, since_ms: int, session_id: str | None = None
    ) -> dict[str, Any]:
        return self.fetch_live_summary_messages(since_ms=since_ms, session_id=session_id)

    def fetch_live_model_usage(
        self, *, since_ms: int, limit: int = 5, session_id: str | None = None
    ) -> list[dict[str, Any]]:
        _ = (since_ms, limit)
        if session_id is not None and session_id != self.session_id:
            return []
        return [
            {
                "model_id": self.model_id,
                "provider_id": "anthropic",
                "input_tokens": 10,
                "output_tokens": 5,
                "cache_read": 0,
                "cache_write": 0,
                "total_sessions": 1,
                "total_interactions": 1,
            }
        ]

    def fetch_live_tool_usage(
        self, *, since_ms: int, limit: int = 8, session_id: str | None = None
    ) -> list[dict[str, Any]]:
        _ = (since_ms, limit, session_id)
        return []

    def resolve_token_source(self, *, days: int | None = None, token_source: str = "auto") -> str:
        _ = days
        return "message" if token_source == "auto" else token_source


def _create_live_fixture(db_path: Path, *, model_id: str = "anthropic/claude-sonnet-4-5") -> None:
    now_ms = int(time.time() * 1000)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE session ("
            "id TEXT PRIMARY KEY, "
            "project_id TEXT, "
            "title TEXT, "
            "directory TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "time_archived INTEGER"
            ")"
        )
        conn.execute("CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT, name TEXT)")
        conn.execute(
            "CREATE TABLE message ("
            "id TEXT PRIMARY KEY, "
            "session_id TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "data TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE part ("
            "id TEXT PRIMARY KEY, "
            "message_id TEXT, "
            "session_id TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "data TEXT"
            ")"
        )

        conn.execute(
            "INSERT INTO project (id, worktree, name) VALUES (?, ?, ?)",
            ("p1", "/tmp/live-proj", "live-proj"),
        )
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p1", "Live Session", "/tmp/live-proj", now_ms, now_ms, None),
        )

        message_payload = {
            "role": "assistant",
            "modelID": model_id,
            "time": {"created": now_ms},
            "tokens": {
                "input": 100,
                "output": 20,
                "cache": {"read": 5, "write": 2},
            },
        }
        conn.execute(
            "INSERT INTO message "
            "(id, session_id, time_created, time_updated, data) VALUES (?, ?, ?, ?, ?)",
            ("m1", "s1", now_ms, now_ms, json.dumps(message_payload)),
        )

        step_payload = {
            "type": "step-finish",
            "tokens": {
                "input": 100,
                "output": 20,
                "cache": {"read": 5, "write": 2},
            },
        }
        tool_payload = {
            "type": "tool",
            "tool": "bash",
            "state": {"status": "completed"},
        }
        conn.execute(
            "INSERT INTO part "
            "(id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("p-step", "m1", "s1", now_ms, now_ms, json.dumps(step_payload)),
        )
        conn.execute(
            "INSERT INTO part "
            "(id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("p-tool", "m1", "s1", now_ms, now_ms, json.dumps(tool_payload)),
        )


def _copy_claudecode_fixtures(destination: Path) -> Path:
    target = destination / ".claude" / "projects"
    shutil.copytree(CLAUDECODE_FIXTURES_DIR, target)
    return destination / ".claude"


def test_get_live_snapshot_returns_activity(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_live_fixture(db_path)

    snapshot = get_live_snapshot(
        settings=AppSettings(opencode_data_dir=tmp_path),
        window_minutes=60,
        db_path_override=db_path,
        token_source="auto",
        models_limit=5,
        tools_limit=5,
    )

    assert snapshot.total_interactions == 1
    assert snapshot.total_sessions == 1
    assert snapshot.usage.input_tokens == 100
    assert snapshot.active_session is not None
    assert snapshot.active_session.is_active is True
    assert len(snapshot.top_models) == 1
    assert snapshot.top_models[0].model_id == "anthropic/claude-sonnet-4-5"
    assert len(snapshot.top_tools) == 1
    assert snapshot.top_tools[0].tool_name == "bash"


def test_live_command_once_json_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_live_fixture(db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["live", "--once", "--json", "--db-path", str(db_path), "--window-minutes", "60"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_interactions"] == 1
    assert payload["token_source"] in {"steps", "message"}


def test_get_live_sessions_includes_recent_claudecode_jsonl_session(tmp_path: Path) -> None:
    claudecode_dir = _copy_claudecode_fixtures(tmp_path)
    session_file = claudecode_dir / "projects" / "-Users-test-projs-myproject" / "session-001.jsonl"
    stale_session_file = (
        claudecode_dir / "projects" / "-Users-test-projs-myproject" / "session-002.jsonl"
    )
    stale_session_file2 = (
        claudecode_dir / "projects" / "-Users-test-projs-myproject" / "session-004.jsonl"
    )
    stale_session_file3 = (
        claudecode_dir / "projects" / "-Users-test-projs-other" / "session-003.jsonl"
    )
    now = time.time()
    os.utime(stale_session_file, (now - 3600, now - 3600))
    os.utime(stale_session_file2, (now - 3600, now - 3600))
    os.utime(stale_session_file3, (now - 3600, now - 3600))
    os.utime(session_file, (now, now))

    settings = AppSettings(
        opencode_data_dir=tmp_path / "nonexistent",
        claudecode_data_dir=claudecode_dir,
        claudecode_enabled=True,
    )

    sessions = get_live_sessions(settings=settings)

    assert len(sessions) == 1
    assert sessions[0].session_id == "local-claudecode:session-001"
    assert sessions[0].project_name == "myproject"
    assert sessions[0].is_active is True


def test_get_live_snapshot_rejects_ambiguous_unprefixed_local_session_id() -> None:
    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeLiveRepo(
                session_id="shared-session",
                project_name="OpenCode",
                model_id="anthropic/open-opus",
            ),
        ),
        (
            "local-claudecode",
            _FakeLiveRepo(
                session_id="shared-session",
                project_name="Claude Code",
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]

    with patch("modelmeter.core.live._resolve_live_repositories", return_value=local_repos):
        try:
            get_live_snapshot(
                settings=settings,
                window_minutes=60,
                token_source="auto",
                models_limit=5,
                tools_limit=5,
                session_id="shared-session",
            )
        except RuntimeError as exc:
            assert "Ambiguous live session `shared-session`" in str(exc)
        else:
            raise AssertionError("Expected ambiguous unprefixed live session ID to raise")


def test_get_live_snapshot_returns_namespaced_id_for_unique_unprefixed_session() -> None:
    settings = AppSettings()
    local_repos = [
        (
            "local-claudecode",
            _FakeLiveRepo(
                session_id="unique-session",
                project_name="Test",
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]

    with patch("modelmeter.core.live._resolve_live_repositories", return_value=local_repos):
        snapshot = get_live_snapshot(
            settings=settings,
            window_minutes=60,
            token_source="auto",
            models_limit=5,
            tools_limit=5,
            session_id="unique-session",
        )
    assert snapshot.active_session is not None
    assert snapshot.active_session.session_id == "local-claudecode:unique-session"


def test_live_snapshot_uses_claudecode_repository_for_claudecode_session(tmp_path: Path) -> None:
    claudecode_dir = _copy_claudecode_fixtures(tmp_path)
    session_file = claudecode_dir / "projects" / "-Users-test-projs-myproject" / "session-001.jsonl"
    now = time.time()
    os.utime(session_file, (now, now))
    settings = AppSettings(
        opencode_data_dir=tmp_path / "nonexistent",
        claudecode_data_dir=claudecode_dir,
        claudecode_enabled=True,
    )

    snapshot = get_live_snapshot(
        settings=settings,
        window_minutes=60 * 24 * 30,
        token_source="auto",
        models_limit=5,
        tools_limit=5,
        session_id="session-001",
    )

    assert snapshot.total_sessions == 1
    assert snapshot.total_interactions > 0
    assert snapshot.active_session is not None
    assert snapshot.active_session.session_id == "local-claudecode:session-001"
    assert snapshot.active_session.project_name == "myproject"
    assert snapshot.active_session.is_active is True
    assert snapshot.active_session.last_updated_ms >= int(now * 1000) - 1000
    assert snapshot.top_models[0].model_id == "anthropic/claude-sonnet-4-6"


def test_live_snapshot_normalizes_providerless_model_ids_across_sources(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_live_fixture(db_path, model_id="anthropic/claude-sonnet-4-6")

    claudecode_dir = _copy_claudecode_fixtures(tmp_path)
    session_file = claudecode_dir / "projects" / "-Users-test-projs-myproject" / "session-001.jsonl"
    now = time.time()
    os.utime(session_file, (now, now))

    pricing_path = tmp_path / "models.json"
    pricing_path.write_text(
        json.dumps(
            {
                "anthropic/claude-sonnet-4-6": {
                    "input_cost_per_1m": 3.0,
                    "output_cost_per_1m": 15.0,
                    "cache_read_cost_per_1m": 0.3,
                    "cache_write_cost_per_1m": 3.75,
                }
            }
        )
    )

    snapshot = get_live_snapshot(
        settings=AppSettings(
            opencode_data_dir=tmp_path,
            opencode_db_path=db_path,
            claudecode_data_dir=claudecode_dir,
            claudecode_enabled=True,
        ),
        window_minutes=60 * 24 * 30,
        pricing_file_override=pricing_path,
        token_source="message",
        models_limit=5,
        tools_limit=5,
    )

    matching = [m for m in snapshot.top_models if m.model_id == "anthropic/claude-sonnet-4-6"]
    assert len(matching) == 1
    assert matching[0].total_interactions >= 2
    assert matching[0].cost_usd is not None
