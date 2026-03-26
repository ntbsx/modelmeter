from __future__ import annotations

import urllib.error
from pathlib import Path
from typing import Any, cast

import pytest

import modelmeter.core.sources as sources_module
from modelmeter.config.settings import AppSettings
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceAuth,
    SourceRegistry,
    SourceRegistryError,
    check_source_health,
    load_source_registry,
    save_source_registry,
)


class _MockResponse:
    def __init__(self, status: int) -> None:
        self.status = status

    def __enter__(self) -> _MockResponse:
        return self

    def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
        _ = (exc_type, exc, tb)


def test_load_source_registry_raises_on_invalid_json(tmp_path: Path) -> None:
    registry_path = tmp_path / "sources.json"
    registry_path.write_text("{invalid json")

    with pytest.raises(SourceRegistryError, match="Invalid source registry JSON"):
        load_source_registry(settings=AppSettings(source_registry_file=registry_path))


def test_save_source_registry_uses_private_file_permissions(tmp_path: Path) -> None:
    registry_path = tmp_path / "sources.json"
    settings = AppSettings(source_registry_file=registry_path)

    save_source_registry(settings=settings, registry=SourceRegistry())

    assert registry_path.exists()
    assert registry_path.stat().st_mode & 0o777 == 0o600


def test_check_source_health_does_not_send_auth_header(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, Any] = {}

    def _mock_urlopen(request: Any, timeout: int) -> _MockResponse:
        captured["url"] = request.full_url
        captured["timeout"] = timeout
        captured["auth"] = request.get_header("Authorization")
        return _MockResponse(status=200)

    monkeypatch.setattr(sources_module.urllib.request, "urlopen", _mock_urlopen)

    health = check_source_health(
        source=DataSourceConfig(
            source_id="remote",
            kind="http",
            base_url="https://example.com/",
            auth=SourceAuth(username="user", password="s3cret"),
        ),
        settings=AppSettings(source_http_timeout_seconds=7),
    )

    assert health.is_reachable is True
    assert captured["url"] == "https://example.com/health"
    assert captured["timeout"] == 7
    # Health endpoint is auth-exempt, so no auth header should be sent
    assert captured["auth"] is None


def test_check_source_health_reports_http_auth_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _mock_urlopen(request: Any, timeout: int) -> _MockResponse:
        _ = (request, timeout)
        raise urllib.error.HTTPError(
            url="https://example.com/health",
            code=401,
            msg="Unauthorized",
            hdrs=cast(Any, None),
            fp=cast(Any, None),
        )

    monkeypatch.setattr(sources_module.urllib.request, "urlopen", _mock_urlopen)

    health = check_source_health(
        source=DataSourceConfig(source_id="remote", kind="http", base_url="https://example.com"),
        settings=AppSettings(),
    )

    assert health.is_reachable is False
    assert health.detail == "HTTP 401"
    assert health.error == "Unauthorized"


def test_data_source_config_jsonl_kind() -> None:
    source = DataSourceConfig(
        source_id="local-claudecode",
        kind="jsonl",
        db_path=Path("/tmp/test"),
    )
    assert source.kind == "jsonl"


def test_data_source_config_agent_field() -> None:
    source = DataSourceConfig(
        source_id="local-opencode",
        kind="sqlite",
        db_path=Path("/tmp/test.db"),
        agent="opencode",
    )
    assert source.agent == "opencode"
