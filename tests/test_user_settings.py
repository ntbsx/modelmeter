"""Tests for file-based user settings store."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

import pytest

from modelmeter.config.user_settings import (
    ALLOWED_KEYS,
    load_user_settings,
    save_user_settings,
)


def _with_settings_path(tmp_path: Path) -> Any:
    """Context manager that redirects the settings file to a temp path."""
    settings_file = tmp_path / "user_settings.json"
    return patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file)


def test_load_returns_empty_dict_when_file_missing(tmp_path: Path) -> None:
    with _with_settings_path(tmp_path):
        result = load_user_settings()
    assert result == {}


def test_load_returns_empty_dict_on_invalid_json(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text("not valid json")
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file):
        result = load_user_settings()
    assert result == {}


def test_save_and_load_roundtrip(tmp_path: Path) -> None:
    with _with_settings_path(tmp_path):
        save_user_settings({"anthropic_api_key": "sk-ant-test", "openai_api_key": "sk-oai-test"})
        result = load_user_settings()
    assert result == {"anthropic_api_key": "sk-ant-test", "openai_api_key": "sk-oai-test"}


def test_save_creates_parent_directories(tmp_path: Path) -> None:
    nested_path = tmp_path / "a" / "b" / "user_settings.json"
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", nested_path):
        save_user_settings({"anthropic_api_key": "sk-ant-test"})
        assert nested_path.exists()


def test_save_omits_none_values(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file):
        save_user_settings({"anthropic_api_key": "sk-ant-test", "openai_api_key": None})
        data = json.loads(settings_file.read_text())
    assert "anthropic_api_key" in data
    assert "openai_api_key" not in data


def test_save_omits_empty_string_values(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file):
        save_user_settings({"anthropic_api_key": "", "openai_api_key": "sk-oai-test"})
        data = json.loads(settings_file.read_text())
    assert "anthropic_api_key" not in data
    assert "openai_api_key" in data


def test_save_rejects_unknown_keys(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file):
        save_user_settings({"anthropic_api_key": "sk-ant-test", "unknown_key": "value"})
        data = json.loads(settings_file.read_text())
    assert "unknown_key" not in data
    assert "anthropic_api_key" in data


def test_load_filters_unknown_keys_from_file(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text(
        json.dumps({"anthropic_api_key": "sk-ant-test", "injected_key": "evil"})
    )
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file):
        result = load_user_settings()
    assert "injected_key" not in result
    assert result["anthropic_api_key"] == "sk-ant-test"


def test_load_filters_non_string_values(tmp_path: Path) -> None:
    settings_file = tmp_path / "user_settings.json"
    settings_file.write_text(json.dumps({"anthropic_api_key": 12345, "openai_api_key": "sk-ok"}))
    with patch("modelmeter.config.user_settings._USER_SETTINGS_PATH", settings_file):
        result = load_user_settings()
    assert "anthropic_api_key" not in result
    assert result["openai_api_key"] == "sk-ok"


def test_save_overwrites_existing_file(tmp_path: Path) -> None:
    with _with_settings_path(tmp_path):
        save_user_settings({"anthropic_api_key": "first"})
        save_user_settings({"anthropic_api_key": "second"})
        result = load_user_settings()
    assert result["anthropic_api_key"] == "second"


def test_allowed_keys_contains_expected_providers() -> None:
    assert "anthropic_api_key" in ALLOWED_KEYS
    assert "openai_api_key" in ALLOWED_KEYS


@pytest.mark.parametrize("key", ["anthropic_api_key", "openai_api_key"])
def test_save_and_load_single_key(tmp_path: Path, key: str) -> None:
    with _with_settings_path(tmp_path):
        save_user_settings({key: "test-value"})
        result = load_user_settings()
    assert result[key] == "test-value"
