from __future__ import annotations

import json
import sqlite3
import time
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from modelmeter.api.app import create_app


def _new_client() -> Any:
    return cast(Any, TestClient(create_app()))


def _get_json(response: Any) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _create_api_fixture(db_path: Path) -> None:
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
            ("p1", "/tmp/api-proj", "api-proj"),
        )
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p1", "API Session", "/tmp/api-proj", now_ms, now_ms, None),
        )

        message_payload = {
            "role": "assistant",
            "modelID": "anthropic/claude-sonnet-4-5",
            "time": {"created": now_ms},
            "tokens": {
                "input": 10,
                "output": 5,
                "cache": {"read": 2, "write": 1},
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
                "input": 10,
                "output": 5,
                "cache": {"read": 2, "write": 1},
            },
        }
        tool_payload = {"type": "tool", "tool": "bash"}
        conn.execute(
            "INSERT INTO part "
            "(id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("p1", "m1", "s1", now_ms, now_ms, json.dumps(step_payload)),
        )
        conn.execute(
            "INSERT INTO part "
            "(id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            ("p2", "m1", "s1", now_ms, now_ms, json.dumps(tool_payload)),
        )


def test_health_endpoint() -> None:
    client = _new_client()
    response = client.get("/health")

    assert response.status_code == 200
    assert _get_json(response) == {"status": "ok"}


def test_doctor_endpoint_with_db_path(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/doctor", params={"db_path": str(db_path)})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["selected_source"] == "sqlite"


def test_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/summary", params={"db_path": str(db_path), "days": 7})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_sessions"] == 1
    assert payload["usage"]["input_tokens"] == 10


def test_models_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/models", params={"db_path": str(db_path), "days": 7})

    assert response.status_code == 200
    payload = _get_json(response)
    assert len(payload["models"]) == 1
    assert payload["models"][0]["model_id"] == "anthropic/claude-sonnet-4-5"


def test_model_detail_not_found_returns_404(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/models/openai/gpt-5",
        params={"db_path": str(db_path), "days": 7},
    )

    assert response.status_code == 404


def test_live_snapshot_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/live/snapshot",
        params={"db_path": str(db_path), "window_minutes": 60, "token_source": "auto"},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_interactions"] >= 1
    assert len(payload["top_tools"]) >= 1
