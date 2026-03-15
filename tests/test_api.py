from __future__ import annotations

import base64
import json
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast

import pytest
from fastapi.testclient import TestClient

import modelmeter.api.app as api_app_module
from modelmeter.api.app import create_app
from modelmeter.config.settings import AppSettings
from modelmeter.core.models import UpdateCheckResponse


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


def _create_daily_boundary_fixture(db_path: Path) -> None:
    boundary_ms = int(datetime(2026, 3, 13, 18, 30, tzinfo=UTC).timestamp() * 1000)
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
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p1", "Boundary Session", "/tmp/boundary", boundary_ms, boundary_ms, None),
        )

        payload = {
            "role": "assistant",
            "modelID": "openai/gpt-5",
            "time": {"created": boundary_ms},
            "tokens": {
                "input": 10,
                "output": 5,
                "cache": {"read": 0, "write": 0},
            },
        }
        conn.execute(
            "INSERT INTO message "
            "(id, session_id, time_created, time_updated, data) VALUES (?, ?, ?, ?, ?)",
            ("m1", "s1", boundary_ms, boundary_ms, json.dumps(payload)),
        )


def test_health_endpoint() -> None:
    client = _new_client()
    response = client.get("/health")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["status"] == "ok"
    assert isinstance(payload["app_version"], str)
    assert payload["app_version"]
    assert payload["auth_required"] is False


def test_health_reports_auth_required_when_password_set() -> None:
    client = _new_client(server_password="secret")
    response = client.get("/health")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["status"] == "ok"
    assert payload["auth_required"] is True


def test_doctor_endpoint_with_db_path(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/api/doctor", params={"db_path": str(db_path)})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["selected_source"] == "sqlite"


def test_update_check_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_update_check(*, settings: AppSettings) -> UpdateCheckResponse:
        _ = settings
        return UpdateCheckResponse(
            current_version="2026.3.1",
            latest_version="2026.3.20",
            update_available=True,
            release_tag="v2026.3.20",
            release_url="https://github.com/ntbsx/modelmeter/releases/tag/v2026.3.20",
            checked_at_ms=1,
        )

    monkeypatch.setattr(api_app_module, "check_for_updates", _mock_update_check)
    client = _new_client()
    response = client.get("/api/update/check")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["update_available"] is True


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
    assert payload["total_models"] == 1
    assert payload["models_offset"] == 0
    assert payload["models_returned"] == 1


def test_providers_endpoint(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/api/providers", params={"db_path": str(db_path), "days": 7})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_providers"] == 1
    assert payload["providers"][0]["provider"] == "anthropic"


def test_models_endpoint_offset_returns_empty_slice(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/models",
        params={"db_path": str(db_path), "days": 7, "offset": 1, "limit": 1},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_models"] == 1
    assert payload["models_offset"] == 1
    assert payload["models_limit"] == 1
    assert payload["models_returned"] == 0
    assert payload["models"] == []


def test_projects_endpoint_pagination_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/projects",
        params={"db_path": str(db_path), "days": 7, "offset": 0, "limit": 20},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_projects"] == 1
    assert payload["projects_offset"] == 0
    assert payload["projects_returned"] == 1
    assert len(payload["projects"]) == 1


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
    assert payload["sessions_returned"] == 1
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


def test_daily_endpoint_uses_timezone_offset_for_day_buckets(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_daily_boundary_fixture(db_path)

    client = _new_client()
    utc_response = client.get(
        "/api/daily",
        params={"db_path": str(db_path), "days": 7, "token_source": "message"},
    )
    assert utc_response.status_code == 200
    utc_payload = _get_json(utc_response)
    assert utc_payload["daily"][0]["day"] == "2026-03-13"

    local_response = client.get(
        "/api/daily",
        params={
            "db_path": str(db_path),
            "days": 7,
            "token_source": "message",
            "timezone_offset_minutes": 420,
        },
    )
    assert local_response.status_code == 200
    local_payload = _get_json(local_response)
    assert local_payload["daily"][0]["day"] == "2026-03-14"


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
    payload = _get_json(response)
    assert payload["detail"] == "Invalid credentials"


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
    payload = _get_json(response)
    assert payload["status"] == "ok"
    assert isinstance(payload["app_version"], str)


def test_spa_routes_are_not_blocked_when_auth_enabled() -> None:
    client = _new_client(server_password="secret")

    root_response = client.get("/")
    login_response = client.get("/login")

    assert root_response.status_code != 401
    assert login_response.status_code != 401


def test_models_endpoint_filters_by_provider(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get(
        "/api/models", params={"db_path": str(db_path), "days": 7, "provider": "anthropic"}
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["total_models"] == 1
    assert payload["models"][0]["model_id"] == "anthropic/claude-sonnet-4-5"
