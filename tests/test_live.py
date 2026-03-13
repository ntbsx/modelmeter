from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path

from typer.testing import CliRunner

from modelmeter.cli.main import app
from modelmeter.config.settings import AppSettings
from modelmeter.core.live import get_live_snapshot


def _create_live_fixture(db_path: Path) -> None:
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
            "modelID": "anthropic/claude-sonnet-4-5",
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
