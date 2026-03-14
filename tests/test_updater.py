from __future__ import annotations

import pytest

import modelmeter.core.updater as updater_module
from modelmeter.config.settings import AppSettings
from modelmeter.core.updater import apply_update, check_for_updates


def test_check_for_updates_reports_available(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_latest_release(
        *, settings: AppSettings
    ) -> tuple[str | None, str | None, str | None, str | None]:
        _ = settings
        return "2026.3.20", "v2026.3.20", "https://gitlab.example/release", None

    monkeypatch.setattr(updater_module, "get_base_version", lambda: "2026.3.1")
    monkeypatch.setattr(updater_module, "_resolve_latest_release", _mock_latest_release)

    result = check_for_updates(settings=AppSettings())

    assert result.current_version == "2026.3.1"
    assert result.latest_version == "2026.3.20"
    assert result.update_available is True


def test_check_for_updates_handles_disabled_setting() -> None:
    result = check_for_updates(settings=AppSettings(update_check_enabled=False))

    assert result.update_available is False
    assert result.error == "Update checks are disabled by configuration."


def test_apply_update_dry_run_returns_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_resolve_install_spec(*, version: str, timeout_seconds: int) -> str:
        _ = timeout_seconds
        return f"https://example.com/modelmeter-{version}.whl"

    monkeypatch.setattr(updater_module, "_resolve_install_spec", _mock_resolve_install_spec)

    spec, command = apply_update(
        settings=AppSettings(),
        version="2026.3.20",
        method="pip",
        dry_run=True,
    )

    assert spec == "https://example.com/modelmeter-2026.3.20.whl"
    assert command[:4] == ["python3", "-m", "pip", "install"]


def test_apply_update_runs_install_command(monkeypatch: pytest.MonkeyPatch) -> None:
    def _mock_resolve_install_spec(*, version: str, timeout_seconds: int) -> str:
        _ = timeout_seconds
        return f"https://example.com/modelmeter-{version}.whl"

    monkeypatch.setattr(updater_module, "_resolve_install_spec", _mock_resolve_install_spec)
    calls: list[list[str]] = []

    def _record(command: list[str]) -> None:
        calls.append(command)

    monkeypatch.setattr(updater_module, "_run_install_command", _record)

    apply_update(
        settings=AppSettings(),
        version="2026.3.20",
        method="auto",
        dry_run=False,
    )

    assert calls
    assert calls[0][-1].endswith("2026.3.20.whl")


def test_apply_update_wraps_network_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    import urllib.error

    def _failing_resolve(*, version: str, timeout_seconds: int) -> str:
        raise urllib.error.URLError("Connection refused")

    monkeypatch.setattr(updater_module, "_resolve_install_spec", _failing_resolve)

    with pytest.raises(RuntimeError, match="Failed to resolve install source"):
        apply_update(
            settings=AppSettings(),
            version="2026.3.20",
            method="auto",
            dry_run=False,
        )
