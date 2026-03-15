"""Tests for get_providers_usage() and the /api/provider-usage endpoint."""

from __future__ import annotations

from pathlib import Path
from typing import Any, cast
from unittest.mock import MagicMock, patch

import httpx
import pytest
from fastapi.testclient import TestClient

from modelmeter.api.app import create_app
from modelmeter.core.provider_usage import get_providers_usage


def _new_client(**kwargs: Any) -> Any:
    return cast(Any, TestClient(create_app(**kwargs)))


def _get_json(response: Any) -> dict[str, Any]:
    return cast(dict[str, Any], response.json())


def _patch_settings_path(tmp_path: Path) -> Any:
    return patch(
        "modelmeter.config.user_settings._USER_SETTINGS_PATH",
        tmp_path / "user_settings.json",
    )


def _mock_httpx_response(
    status_code: int = 200,
    json_body: dict[str, Any] | None = None,
    headers: dict[str, str] | None = None,
) -> MagicMock:
    mock_resp = MagicMock(spec=httpx.Response)
    mock_resp.status_code = status_code
    mock_resp.json.return_value = json_body or {}
    mock_resp.headers = httpx.Headers(headers or {})
    if status_code >= 400:
        mock_resp.text = "error"
        http_err = httpx.HTTPStatusError("error", request=MagicMock(), response=mock_resp)
        mock_resp.raise_for_status.side_effect = http_err
    else:
        mock_resp.raise_for_status.return_value = None
    return mock_resp


# ---------------------------------------------------------------------------
# Unit tests for get_providers_usage()
# ---------------------------------------------------------------------------


def test_not_configured_when_no_keys() -> None:
    result = get_providers_usage(anthropic_api_key=None, openai_api_key=None, timeout=5)
    providers = {p.provider: p for p in result.providers}
    assert providers["anthropic"].configured is False
    assert providers["anthropic"].status == "not_configured"
    assert providers["openai"].configured is False
    assert providers["openai"].status == "not_configured"


def test_anthropic_ok_response() -> None:
    mock_resp = _mock_httpx_response(
        json_body={"data": [{"id": "claude-opus-4-5"}, {"id": "claude-sonnet-4-6"}]},
        headers={
            "anthropic-ratelimit-requests-limit": "1000",
            "anthropic-ratelimit-requests-remaining": "999",
            "anthropic-ratelimit-tokens-limit": "100000",
            "anthropic-ratelimit-tokens-remaining": "95000",
        },
    )
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = get_providers_usage(
            anthropic_api_key="sk-ant-test", openai_api_key=None, timeout=5
        )

    provider = next(p for p in result.providers if p.provider == "anthropic")
    assert provider.configured is True
    assert provider.status == "ok"
    assert provider.models_count == 2
    assert "claude-opus-4-5" in provider.models
    assert provider.rate_limits is not None
    assert provider.rate_limits.requests_limit == 1000
    assert provider.rate_limits.requests_remaining == 999
    assert provider.rate_limits.tokens_limit == 100000
    assert provider.rate_limits.tokens_remaining == 95000


def test_anthropic_invalid_key_returns_error() -> None:
    mock_resp = _mock_httpx_response(status_code=401)
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = get_providers_usage(anthropic_api_key="sk-ant-bad", openai_api_key=None, timeout=5)

    provider = next(p for p in result.providers if p.provider == "anthropic")
    assert provider.configured is True
    assert provider.status == "error"
    assert provider.error is not None
    assert "401" in provider.error


def test_anthropic_http_error_returns_error() -> None:
    mock_resp = _mock_httpx_response(status_code=500)
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = get_providers_usage(
            anthropic_api_key="sk-ant-test", openai_api_key=None, timeout=5
        )

    provider = next(p for p in result.providers if p.provider == "anthropic")
    assert provider.status == "error"
    assert "500" in (provider.error or "")


def test_anthropic_request_error_returns_error() -> None:
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.side_effect = httpx.ConnectError(
            "connection refused"
        )
        result = get_providers_usage(
            anthropic_api_key="sk-ant-test", openai_api_key=None, timeout=5
        )

    provider = next(p for p in result.providers if p.provider == "anthropic")
    assert provider.status == "error"
    assert provider.error is not None


def test_openai_ok_response() -> None:
    mock_resp = _mock_httpx_response(
        json_body={"data": [{"id": "gpt-4o"}, {"id": "gpt-4o-mini"}, {"id": "gpt-4o"}]},
        headers={
            "x-ratelimit-limit-requests": "500",
            "x-ratelimit-remaining-requests": "498",
        },
    )
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = get_providers_usage(
            anthropic_api_key=None, openai_api_key="sk-oai-test", timeout=5
        )

    provider = next(p for p in result.providers if p.provider == "openai")
    assert provider.configured is True
    assert provider.status == "ok"
    # Deduped: gpt-4o appears twice but models_count should be 2
    assert provider.models_count == 2
    assert provider.rate_limits is not None
    assert provider.rate_limits.requests_limit == 500
    assert provider.rate_limits.requests_remaining == 498


def test_openai_invalid_key_returns_error() -> None:
    mock_resp = _mock_httpx_response(status_code=401)
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = get_providers_usage(anthropic_api_key=None, openai_api_key="sk-bad", timeout=5)

    provider = next(p for p in result.providers if p.provider == "openai")
    assert provider.status == "error"
    assert "401" in (provider.error or "")


def test_openai_request_error_returns_error() -> None:
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.side_effect = (
            httpx.TimeoutException("timeout")
        )
        result = get_providers_usage(
            anthropic_api_key=None, openai_api_key="sk-oai-test", timeout=5
        )

    provider = next(p for p in result.providers if p.provider == "openai")
    assert provider.status == "error"


def test_both_providers_returned_regardless_of_config() -> None:
    result = get_providers_usage(anthropic_api_key=None, openai_api_key=None, timeout=5)
    provider_names = [p.provider for p in result.providers]
    assert "anthropic" in provider_names
    assert "openai" in provider_names


def test_rate_limits_none_when_headers_missing() -> None:
    mock_resp = _mock_httpx_response(
        json_body={"data": [{"id": "claude-opus-4-5"}]},
    )
    with patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        result = get_providers_usage(
            anthropic_api_key="sk-ant-test", openai_api_key=None, timeout=5
        )

    provider = next(p for p in result.providers if p.provider == "anthropic")
    assert provider.rate_limits is not None
    assert provider.rate_limits.requests_limit is None
    assert provider.rate_limits.tokens_limit is None


# ---------------------------------------------------------------------------
# Integration tests via /api/provider-usage endpoint
# ---------------------------------------------------------------------------


def test_provider_usage_endpoint_no_keys_configured(tmp_path: Path) -> None:
    with _patch_settings_path(tmp_path):
        client = _new_client()
        response = client.get("/api/provider-usage")

    assert response.status_code == 200
    payload = _get_json(response)
    providers = {p["provider"]: p for p in payload["providers"]}
    assert providers["anthropic"]["configured"] is False
    assert providers["openai"]["configured"] is False


def test_provider_usage_endpoint_uses_user_saved_key(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text('{"anthropic_api_key": "sk-ant-saved"}')

    mock_resp = _mock_httpx_response(
        json_body={"data": [{"id": "claude-opus-4-5"}]},
    )
    with _patch_settings_path(tmp_path), patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        client = _new_client()
        response = client.get("/api/provider-usage")

    assert response.status_code == 200
    payload = _get_json(response)
    providers = {p["provider"]: p for p in payload["providers"]}
    assert providers["anthropic"]["configured"] is True
    assert providers["anthropic"]["status"] == "ok"


@pytest.mark.parametrize(
    "env_var,provider",
    [
        ("MODELMETER_ANTHROPIC_API_KEY", "anthropic"),
        ("MODELMETER_OPENAI_API_KEY", "openai"),
    ],
)
def test_provider_usage_endpoint_uses_env_var(
    tmp_path: Path, monkeypatch: Any, env_var: str, provider: str
) -> None:
    monkeypatch.setenv(env_var, "sk-test-env")
    mock_resp = _mock_httpx_response(json_body={"data": [{"id": "some-model"}]})
    with _patch_settings_path(tmp_path), patch("httpx.Client") as mock_client_cls:
        mock_client_cls.return_value.__enter__.return_value.get.return_value = mock_resp
        client = _new_client()
        response = client.get("/api/provider-usage")

    assert response.status_code == 200
    payload = _get_json(response)
    providers = {p["provider"]: p for p in payload["providers"]}
    assert providers[provider]["configured"] is True
    assert providers[provider]["status"] == "ok"
