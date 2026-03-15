"""Tests for GET /api/settings and PUT /api/settings endpoints."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import patch

from fastapi.testclient import TestClient

from modelmeter.api.app import create_app


def _new_client(**kwargs: Any) -> Any:
    return cast(Any, TestClient(create_app(**kwargs)))


def _get_json(response: Any) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _patch_settings_path(tmp_path: Path) -> Any:
    return patch(
        "modelmeter.config.user_settings._USER_SETTINGS_PATH",
        tmp_path / "user_settings.json",
    )


# ---------------------------------------------------------------------------
# GET /api/settings
# ---------------------------------------------------------------------------


def test_get_settings_returns_not_configured_by_default(tmp_path: Path) -> None:
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.get("/api/settings")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"] == {"configured": False, "source": None}
    assert payload["openai_api_key"] == {"configured": False, "source": None}


def test_get_settings_shows_env_source_when_env_var_set(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("MODELMETER_ANTHROPIC_API_KEY", "sk-ant-env")
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.get("/api/settings")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"] == {"configured": True, "source": "env"}
    assert payload["openai_api_key"] == {"configured": False, "source": None}


def test_get_settings_shows_user_source_when_key_saved(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text('{"openai_api_key": "sk-oai-saved"}')
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.get("/api/settings")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["openai_api_key"] == {"configured": True, "source": "user"}
    assert payload["anthropic_api_key"] == {"configured": False, "source": None}


def test_get_settings_env_takes_priority_over_user_file(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("MODELMETER_ANTHROPIC_API_KEY", "sk-ant-env")
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text('{"anthropic_api_key": "sk-ant-saved"}')
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.get("/api/settings")

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"] == {"configured": True, "source": "env"}


def test_get_settings_never_returns_key_value(tmp_path: Path, monkeypatch: Any) -> None:
    monkeypatch.setenv("MODELMETER_ANTHROPIC_API_KEY", "sk-ant-secret")
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text('{"openai_api_key": "sk-oai-secret"}')
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.get("/api/settings")

    assert response.status_code == 200
    body = response.text
    assert "sk-ant-secret" not in body
    assert "sk-oai-secret" not in body


# ---------------------------------------------------------------------------
# PUT /api/settings
# ---------------------------------------------------------------------------


def test_put_settings_saves_anthropic_key(tmp_path: Path) -> None:
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.put("/api/settings", json={"anthropic_api_key": "sk-ant-new"})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"] == {"configured": True, "source": "user"}


def test_put_settings_saves_openai_key(tmp_path: Path) -> None:
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.put("/api/settings", json={"openai_api_key": "sk-oai-new"})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["openai_api_key"] == {"configured": True, "source": "user"}


def test_put_settings_clears_key_with_null(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text('{"anthropic_api_key": "sk-ant-old"}')
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.put("/api/settings", json={"anthropic_api_key": None})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"] == {"configured": False, "source": None}


def test_put_settings_omitted_field_is_not_changed(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text('{"anthropic_api_key": "sk-ant-kept"}')
    with _patch_settings_path(tmp_path):
        client = _new_client()
        # Only send openai key, anthropic should remain unchanged
        response = client.put("/api/settings", json={"openai_api_key": "sk-oai-new"})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"] == {"configured": True, "source": "user"}
    assert payload["openai_api_key"] == {"configured": True, "source": "user"}


def test_put_settings_persists_to_disk(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    import json

    with _patch_settings_path(tmp_path):
        client = _new_client()
        client.put("/api/settings", json={"openai_api_key": "sk-oai-persisted"})

    data = json.loads(settings_file.read_text())
    assert data["openai_api_key"] == "sk-oai-persisted"


def test_put_settings_returns_updated_status(tmp_path: Path) -> None:
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.put(
            "/api/settings",
            json={"anthropic_api_key": "sk-ant-new", "openai_api_key": "sk-oai-new"},
        )

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"]["configured"] is True
    assert payload["openai_api_key"]["configured"] is True


def test_put_settings_env_var_key_reported_as_env_not_user(
    tmp_path: Path, monkeypatch: Any
) -> None:
    monkeypatch.setenv("MODELMETER_ANTHROPIC_API_KEY", "sk-ant-env")
    with _patch_settings_path(tmp_path):
        client = _new_client()
        # Even if user tries to save via UI, env var takes precedence in response
        response = client.put("/api/settings", json={"anthropic_api_key": "sk-ant-ui"})

    assert response.status_code == 200
    payload = _get_json(response)
    assert payload["anthropic_api_key"]["source"] == "env"
