from __future__ import annotations

import base64
import json
import sqlite3
import time
from pathlib import Path
from typing import Any, cast

from fastapi.testclient import TestClient

from modelmeter.api.app import create_app


def _new_client(**create_app_kwargs: Any) -> Any:
    return cast(Any, TestClient(create_app(**create_app_kwargs)))


def _get_json(response: Any) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _basic_auth_headers(username: str, password: str) -> dict[str, str]:
    token = base64.b64encode(f"{username}:{password}".encode()).decode("ascii")
    return {"Authorization": f"Basic {token}"}


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
    response = client.get("/api/doctor", params={"db_path": str(db_path)})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["selected_source"] == "sqlite"


def test_summary_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/api/summary", params={"db_path": str(db_path), "days": 7})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_sessions"] == 1
    assert payload["usage"]["input_tokens"] == 10


def test_models_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/api/models", params={"db_path": str(db_path), "days": 7})

    assert response.status_code == 200
    payload = _get_json(response)
    assert len(payload["models"]) == 1
    assert payload["models"][0]["model_id"] == "anthropic/claude-sonnet-4-5"


def test_model_detail_not_found_returns_404(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/models/openai/gpt-5",
        params={"db_path": str(db_path), "days": 7},
    )

    assert response.status_code == 404


def test_project_detail_endpoint_returns_sessions(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/projects/p1",
        params={"db_path": str(db_path), "days": 7},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["project_id"] == "p1"
    assert payload["total_sessions"] == 1
    assert len(payload["sessions"]) == 1
    assert payload["sessions"][0]["session_id"] == "s1"


def test_project_detail_not_found_returns_404(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/projects/unknown-project",
        params={"db_path": str(db_path), "days": 7},
    )

    assert response.status_code == 404


def test_live_snapshot_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/live/snapshot",
        params={"db_path": str(db_path), "window_minutes": 60, "token_source": "auto"},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_interactions"] >= 1
    assert len(payload["top_tools"]) >= 1


def test_live_events_endpoint_streams_sse(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    with client.stream(
        "GET",
        "/api/live/events",
        params={"db_path": str(db_path), "window_minutes": 60, "interval_seconds": 1, "once": True},
    ) as response:
        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")

        first_chunk = ""
        for chunk in response.iter_text():
            if chunk.strip():
                first_chunk = chunk
                break

        assert "event: live.snapshot" in first_chunk
        assert "data:" in first_chunk


def test_doc_alias_redirects_to_docs() -> None:
    client = _new_client()
    response = client.get("/doc", follow_redirects=False)

    assert response.status_code in {302, 307}
    assert response.headers["location"] == "/docs"


def test_auth_enabled_requires_credentials(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret")
    response = client.get("/api/doctor", params={"db_path": str(db_path)})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="ModelMeter"'


def test_auth_enabled_rejects_invalid_credentials(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret")
    response = client.get(
        "/api/doctor",
        params={"db_path": str(db_path)},
        headers=_basic_auth_headers("wrong", "creds"),
    )

    assert response.status_code == 401


def test_auth_enabled_accepts_valid_credentials(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret", server_username="alice")
    response = client.get(
        "/api/doctor",
        params={"db_path": str(db_path)},
        headers=_basic_auth_headers("alice", "secret"),
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["selected_source"] == "sqlite"


def test_health_is_public_even_when_auth_enabled() -> None:
    client = _new_client(server_password="secret")
    response = client.get("/health")

    assert response.status_code == 200
    assert _get_json(response) == {"status": "ok"}
