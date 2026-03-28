from __future__ import annotations

import base64
import json
import os
import shutil
import sqlite3
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

import modelmeter.api.app as api_app_module
from modelmeter.api.app import create_app
from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import _canonical_project_id
from modelmeter.core.models import UpdateCheckResponse

CLAUDECODE_FIXTURES_DIR = Path(__file__).parent / "fixtures" / "claudecode"


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


def _copy_claudecode_fixtures(destination: Path) -> Path:
    target = destination / ".claude" / "projects"
    shutil.copytree(CLAUDECODE_FIXTURES_DIR, target)
    return destination / ".claude"


def _create_daily_boundary_fixture(db_path: Path) -> tuple[str, str]:
    """Create fixture with a timestamp at 18:30 UTC two days ago.

    Returns (utc_day, local_day) where local_day is the day when viewed
    at UTC+7 (timezone_offset_minutes=420): 18:30 UTC + 7h = 01:30 next day.
    """
    from datetime import timedelta

    base_date = datetime.now(tz=UTC).date() - timedelta(days=2)
    boundary_ms = int(
        datetime(base_date.year, base_date.month, base_date.day, 18, 30, tzinfo=UTC).timestamp()
        * 1000
    )
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

    utc_day = base_date.isoformat()
    local_day = (base_date + timedelta(days=1)).isoformat()
    return utc_day, local_day


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


def test_health_includes_agents_detected(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    claudecode_dir = _copy_claudecode_fixtures(tmp_path)
    monkeypatch.setenv("MODELMETER_OPENCODE_DATA_DIR", str(tmp_path / "missing-opencode"))
    monkeypatch.setenv("MODELMETER_CLAUDECODE_DATA_DIR", str(claudecode_dir))
    monkeypatch.setenv("MODELMETER_CLAUDECODE_ENABLED", "true")

    client = _new_client()
    response = client.get("/health")

    assert response.status_code == 200
    data = _get_json(response)
    assert "agents_detected" in data
    assert data["agents_detected"] == ["claudecode"]


def test_doctor_endpoint_with_db_path(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    response = client.get("/api/doctor", params={"db_path": str(db_path)})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["selected_source"] == "sqlite"


def test_sources_endpoint_returns_empty_registry_by_default(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))
    client = _new_client()
    client.cookies.set("ignore", "1")
    response = client.get("/api/sources", headers={"X-Ignore": "1"})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["version"] == 1
    assert payload["sources"] == []


def test_sources_endpoint_redacts_credentials(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "source_id": "remote",
                        "kind": "http",
                        "base_url": "http://example.com",
                        "auth": {"username": "user", "password": "s3cret"},
                    }
                ],
            }
        )
    )
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    client = _new_client()
    response = client.get("/api/sources")

    assert response.status_code == 200
    payload = _get_json(response)
    source = payload["sources"][0]
    assert source["has_auth"] is True
    assert "auth" not in source
    assert "password" not in json.dumps(source)


def test_sources_check_endpoint_reports_reachability(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "source_id": "local",
                        "kind": "sqlite",
                        "db_path": str(db_path),
                    }
                ],
            }
        )
    )
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    client = _new_client()
    response = client.get("/api/sources/check")

    assert response.status_code == 200
    payload = cast(list[dict[str, Any]], response.json())
    assert payload[0]["source_id"] == "local"
    assert payload[0]["is_reachable"] is True


def test_sources_upsert_endpoint_saves_sqlite_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    client = _new_client()
    response = client.put(
        "/api/sources/work-laptop",
        json={
            "kind": "sqlite",
            "label": "Work laptop",
            "db_path": str(tmp_path / "opencode.db"),
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["sources"][0]["source_id"] == "work-laptop"
    assert payload["sources"][0]["kind"] == "sqlite"
    assert payload["sources"][0]["db_path"] == str(tmp_path / "opencode.db")


def test_sources_upsert_endpoint_saves_jsonl_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    jsonl_dir = tmp_path / "claudecode-data"
    jsonl_dir.mkdir()
    (jsonl_dir / "projects").mkdir()

    client = _new_client()
    response = client.put(
        "/api/sources/local-jsonl",
        json={
            "kind": "jsonl",
            "label": "Claude Code data",
            "db_path": str(jsonl_dir),
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["sources"][0]["source_id"] == "local-jsonl"
    assert payload["sources"][0]["kind"] == "jsonl"
    assert payload["sources"][0]["db_path"] == str(jsonl_dir)


def test_sources_upsert_endpoint_persists_agent_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    jsonl_dir = tmp_path / "claudecode-data"
    jsonl_dir.mkdir()
    (jsonl_dir / "projects").mkdir()

    client = _new_client()
    response = client.put(
        "/api/sources/local-jsonl",
        json={
            "kind": "jsonl",
            "label": "Claude Code data",
            "agent": "claudecode",
            "db_path": str(jsonl_dir),
            "enabled": True,
        },
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["sources"][0]["agent"] == "claudecode"


def test_sources_upsert_endpoint_preserves_existing_http_auth(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "source_id": "remote",
                        "kind": "http",
                        "base_url": "https://example.com",
                        "auth": {"username": "user", "password": "s3cret"},
                    }
                ],
            }
        )
    )
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    client = _new_client()
    response = client.put(
        "/api/sources/remote",
        json={
            "kind": "http",
            "base_url": "https://example.com",
            "label": "Remote",
            "enabled": True,
            "preserve_existing_auth": True,
        },
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["sources"][0]["has_auth"] is True


def test_sources_remove_endpoint_deletes_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text(
        json.dumps(
            {
                "version": 1,
                "sources": [
                    {
                        "source_id": "old-source",
                        "kind": "sqlite",
                        "db_path": str(tmp_path / "opencode.db"),
                    }
                ],
            }
        )
    )
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    client = _new_client()
    response = client.delete("/api/sources/old-source")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["removed"] is True

    list_response = client.get("/api/sources")
    list_payload = _get_json(list_response)
    assert list_payload["sources"] == []


def test_sources_endpoint_reports_invalid_registry(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text("{invalid json")
    monkeypatch.setenv("MODELMETER_SOURCE_REGISTRY_FILE", str(registry_path))

    client = _new_client()
    response = client.get("/api/sources")

    assert response.status_code == 500
    payload = _get_json(response)
    assert "Invalid source registry JSON" in payload["detail"]


def test_auth_check_endpoint_requires_credentials_when_auth_enabled() -> None:
    client = _new_client(server_password="secret")

    unauthorized = client.get("/api/auth/check")
    authorized = client.get(
        "/api/auth/check",
        headers=_basic_auth_headers("modelmeter", "secret"),
    )

    assert unauthorized.status_code == 401
    assert authorized.status_code == 200
    payload = _get_json(authorized)
    assert payload["status"] == "ok"


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
    utc_day, local_day = _create_daily_boundary_fixture(db_path)

    client = _new_client()
    utc_response = client.get(
        "/api/daily",
        params={"db_path": str(db_path), "days": 7, "token_source": "message"},
    )
    assert utc_response.status_code == 200
    utc_payload = _get_json(utc_response)
    assert utc_payload["daily"][0]["day"] == utc_day

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
    assert local_payload["daily"][0]["day"] == local_day


def test_date_insights_endpoint_returns_daily_breakdowns(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    today = datetime.now(tz=UTC).date().isoformat()
    response = client.get(
        "/api/date-insights",
        params={"db_path": str(db_path), "day": today, "timezone_offset_minutes": 0},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["day"] == today
    assert payload["total_sessions"] == 1
    assert payload["total_interactions"] == 1
    assert payload["usage"]["total_tokens"] == 18
    assert payload["models"][0]["model_id"] == "anthropic/claude-sonnet-4-5"
    assert payload["providers"][0]["provider"] == "anthropic"
    assert payload["projects"][0]["project_id"] == _canonical_project_id("p1", "/tmp/api-proj")


def test_date_insights_sessions_field(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client()
    today = datetime.now(tz=UTC).date().isoformat()
    response = client.get(
        "/api/date-insights",
        params={"db_path": str(db_path), "day": today, "timezone_offset_minutes": 0},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    sessions = payload["sessions"]
    assert isinstance(sessions, list)
    assert len(sessions) == 1  # type: ignore[reportUnknownArgumentType]
    session = sessions[0]  # type: ignore[reportUnknownVariableType]
    assert session["session_id"] == "s1"
    assert session["project_id"] == "p1"
    assert session["total_tokens"] > 0
    assert session["total_interactions"] == 1
    assert isinstance(session["models"], list)
    assert len(session["models"]) == 1  # type: ignore[reportUnknownArgumentType]
    assert session["models"][0]["model_id"] == "anthropic/claude-sonnet-4-5"
    assert session["started_at"] is not None


def test_date_insights_endpoint_rejects_invalid_day_format() -> None:
    client = _new_client()
    response = client.get("/api/date-insights", params={"day": "03-20-2026"})

    assert response.status_code == 400
    payload = _get_json(response)
    assert payload["detail"] == "Invalid day format. Use YYYY-MM-DD."


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


def test_auth_via_query_param_is_accepted(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret", server_username="alice")
    token = base64.b64encode(b"alice:secret").decode("ascii")
    response = client.get(
        "/api/doctor",
        params={"db_path": str(db_path), "_auth": token},
    )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["selected_source"] == "sqlite"


def test_auth_via_invalid_query_param_is_rejected(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret")
    token = base64.b64encode(b"wrong:creds").decode("ascii")
    response = client.get(
        "/api/doctor",
        params={"db_path": str(db_path), "_auth": token},
    )

    assert response.status_code == 401


def test_sse_endpoint_401_omits_www_authenticate_header(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret")
    response = client.get(
        "/api/live/events",
        params={"db_path": str(db_path), "once": "true"},
    )

    assert response.status_code == 401
    assert "www-authenticate" not in response.headers


def test_non_sse_endpoint_401_includes_www_authenticate_header(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret")
    response = client.get("/api/doctor", params={"db_path": str(db_path)})

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == 'Basic realm="ModelMeter"'


def test_sse_endpoint_accepts_auth_query_param(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    client = _new_client(server_password="secret", server_username="alice")
    token = base64.b64encode(b"alice:secret").decode("ascii")
    response = client.get(
        "/api/live/events",
        params={
            "db_path": str(db_path),
            "window_minutes": 60,
            "interval_seconds": 1,
            "once": "true",
            "_auth": token,
        },
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")


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


def test_list_sessions_returns_recent_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/sessions returns recent sessions with metadata."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()
    response = client.get("/api/sessions", params={"limit": 10})

    assert response.status_code == 200
    data = cast(list[dict[str, Any]], response.json())
    assert isinstance(data, list)
    assert len(data) > 0

    session: dict[str, Any] = data[0]
    assert "session_id" in session
    assert "title" in session
    assert "project_name" in session
    assert "time_created" in session
    assert "time_updated" in session
    assert "message_count" in session
    assert "model_count" in session
    assert "token_count" in session
    assert "is_active" in session


def test_list_sessions_includes_claudecode_sessions(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    claudecode_dir = _copy_claudecode_fixtures(tmp_path)
    session_file = claudecode_dir / "projects" / "-Users-test-projs-myproject" / "session-001.jsonl"
    now = time.time()
    os.utime(session_file, (now, now))
    monkeypatch.setenv("MODELMETER_OPENCODE_DATA_DIR", str(tmp_path / "missing-opencode"))
    monkeypatch.setenv("MODELMETER_CLAUDECODE_DATA_DIR", str(claudecode_dir))
    monkeypatch.setenv("MODELMETER_CLAUDECODE_ENABLED", "true")

    client = _new_client()
    response = client.get("/api/sessions", params={"limit": 10})

    assert response.status_code == 200
    data = cast(list[dict[str, Any]], response.json())
    session = next(
        session for session in data if session["session_id"] == "local-claudecode:session-001"
    )
    assert session["is_active"] is True
    assert session["time_updated"] >= int(now * 1000) - 1000
    assert session["agent"] == "claudecode"


def test_list_sessions_respects_limit_parameter(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/sessions respects the limit parameter."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()

    # Request only 2 sessions
    response = client.get("/api/sessions", params={"limit": 2})
    assert response.status_code == 200
    data = cast(list[dict[str, Any]], response.json())
    assert len(data) <= 2

    # Request 20 sessions (more than available)
    response = client.get("/api/sessions", params={"limit": 20})
    assert response.status_code == 200
    data_larger = cast(list[dict[str, Any]], response.json())
    assert len(data_larger) >= len(data)


def test_list_sessions_includes_archived_when_requested(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/sessions can include archived sessions."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()

    # Without archived sessions
    response = client.get("/api/sessions", params={"include_archived": False})
    assert response.status_code == 200
    data_no_archived = cast(list[dict[str, Any]], response.json())
    assert not any(s.get("time_archived") for s in data_no_archived)

    # With archived sessions
    response = client.get("/api/sessions", params={"include_archived": True})
    assert response.status_code == 200
    # Just verify endpoint doesn't crash
    response.json()


def test_list_sessions_rejects_non_self_source_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/sessions rejects federation scopes (not implemented yet)."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()

    # Try with 'all' scope (should fail)
    response = client.get("/api/sessions", params={"source_scope": "all"})
    assert response.status_code == 501
    assert "not yet implemented" in response.json()["detail"]

    # Try with specific source scope (should fail)
    response = client.get("/api/sessions", params={"source_scope": "source:remote"})
    assert response.status_code == 501


def test_live_session_snapshot_filters_by_session_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/live/session/{session_id} filters to that session."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()

    # First, get a list of sessions
    response = client.get("/api/sessions", params={"limit": 1})
    assert response.status_code == 200
    sessions = cast(list[dict[str, Any]], response.json())
    assert len(sessions) > 0
    session_id = sessions[0]["session_id"]

    # Get live snapshot for that specific session
    response = client.get(f"/api/live/session/{session_id}", params={"window_minutes": 60})
    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "generated_at_ms" in data
    assert "window_minutes" in data
    assert "total_interactions" in data
    assert "total_sessions" in data
    assert "usage" in data
    assert "active_session" in data
    assert "top_models" in data
    assert "top_tools" in data


def test_live_session_events_once_returns_snapshot_event(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/live/session/{session_id}/events emits live.snapshot when once=true."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)
    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()
    sessions_response = client.get("/api/sessions", params={"limit": 1})
    sessions = cast(list[dict[str, Any]], sessions_response.json())
    session_id = sessions[0]["session_id"]

    response = client.get(
        f"/api/live/session/{session_id}/events",
        params={"once": True, "window_minutes": 60},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: live.snapshot" in response.text


def test_live_session_events_rejects_non_local_scope(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/live/session/{session_id}/events emits live.error for unsupported scopes."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)
    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()
    sessions_response = client.get("/api/sessions", params={"limit": 1})
    sessions = cast(list[dict[str, Any]], sessions_response.json())
    session_id = sessions[0]["session_id"]

    response = client.get(
        f"/api/live/session/{session_id}/events",
        params={"once": True, "source_scope": "all"},
    )

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/event-stream")
    assert "event: live.error" in response.text


def test_list_sessions_filters_by_active_since_hours(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Test that /api/sessions excludes sessions older than active_since_hours."""
    db_path = tmp_path / "opencode.db"
    _create_api_fixture(db_path)

    now_ms = int(time.time() * 1000)
    old_ms = now_ms - (29 * 60 * 60 * 1000)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("old-session", "p1", "Old Session", "/tmp/api-proj", old_ms, old_ms, None),
        )
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("new-session", "p1", "New Session", "/tmp/api-proj", now_ms, now_ms, None),
        )

    monkeypatch.setenv("MODELMETER_OPENCODE_DB_PATH", str(db_path))

    client = _new_client()

    response = client.get("/api/sessions", params={"limit": 100, "active_since_hours": 6})
    assert response.status_code == 200
    filtered = cast(list[dict[str, Any]], response.json())
    filtered_ids = {row["session_id"] for row in filtered}
    assert "local-opencode:new-session" in filtered_ids
    assert "local-opencode:old-session" not in filtered_ids

    response_all = client.get("/api/sessions", params={"limit": 100})
    assert response_all.status_code == 200
    unfiltered = cast(list[dict[str, Any]], response_all.json())
    unfiltered_ids = {row["session_id"] for row in unfiltered}
    assert "local-opencode:old-session" in unfiltered_ids


class _FakeLiveSessionRepo:
    def __init__(self, *, model_id: str, project_id: str, project_name: str) -> None:
        self.model_id = model_id
        self.project_id = project_id
        self.project_name = project_name

    def fetch_sessions_summary(
        self,
        *,
        limit: int = 20,
        include_archived: bool = False,
        min_time_updated_ms: int | None = None,
    ) -> list[dict[str, Any]]:
        _ = (limit, include_archived, min_time_updated_ms)
        return [
            {
                "session_id": "shared-session",
                "title": "Shared Session",
                "directory": "/tmp/demo",
                "time_created": 1000,
                "time_updated": 2000,
                "time_archived": None,
                "project_name": self.project_name,
                "project_id": self.project_id,
                "message_count": 1,
                "model_count": 1,
                "token_count": 15,
            }
        ]

    def fetch_active_session(self, *, session_id: str | None = None) -> dict[str, Any] | None:
        if session_id is not None and session_id != "shared-session":
            return None
        return {
            "id": "shared-session",
            "title": "Shared Session",
            "directory": "/tmp/demo",
            "project_id": self.project_id,
            "time_updated": 2000,
            "project_name": self.project_name,
        }

    def fetch_live_summary_messages(
        self, *, since_ms: int, session_id: str | None = None
    ) -> dict[str, Any]:
        _ = since_ms
        if session_id is not None and session_id != "shared-session":
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
        if session_id is not None and session_id != "shared-session":
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


def test_list_sessions_namespaces_local_ids_and_live_route_disambiguates() -> None:
    local_repos = [
        (
            "local-opencode",
            _FakeLiveSessionRepo(
                model_id="anthropic/open-opus",
                project_id="p1",
                project_name="OpenCode",
            ),
        ),
        (
            "local-claudecode",
            _FakeLiveSessionRepo(
                model_id="claude-sonnet-4-6",
                project_id="p2",
                project_name="Claude Code",
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        client = _new_client()

        sessions_response = client.get("/api/sessions", params={"limit": 10})
        assert sessions_response.status_code == 200
        sessions = cast(list[dict[str, Any]], sessions_response.json())
        assert {session["session_id"] for session in sessions} == {
            "local-opencode:shared-session",
            "local-claudecode:shared-session",
        }

        live_response = client.get(
            "/api/live/session/local-claudecode:shared-session",
            params={"window_minutes": 60},
        )
        assert live_response.status_code == 200
        data = live_response.json()
        assert data["active_session"]["project_name"] == "Claude Code"
        assert data["top_models"][0]["model_id"] == "anthropic/claude-sonnet-4-6"
        assert data["active_session"]["session_id"] == "local-claudecode:shared-session", (
            f"Expected namespaced session ID, got {data['active_session']['session_id']}"
        )

        snapshot_response = client.get(
            "/api/live/snapshot",
            params={"window_minutes": 60},
        )
        assert snapshot_response.status_code == 200
        snapshot = snapshot_response.json()
        assert snapshot["active_session"]["session_id"] == "local-opencode:shared-session", (
            "Expected aggregated live snapshot to namespace the active session ID"
        )
