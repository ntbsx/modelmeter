from __future__ import annotations

import pytest

from modelmeter.config.settings import AppSettings
from modelmeter.core.updater import apply_update, check_for_updates


def test_check_for_updates_reports_available(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "modelmeter.core.updater.get_base_version",
        lambda: "2026.3.1",
    )
    monkeypatch.setattr(
        "modelmeter.core.updater._resolve_latest_release",
        lambda *, settings: ("2026.3.20", "v2026.3.20", "https://gitlab.example/release", None),
    )

    result = check_for_updates(settings=AppSettings())

    assert result.current_version == "2026.3.1"
    assert result.latest_version == "2026.3.20"
    assert result.update_available is True


def test_check_for_updates_handles_disabled_setting() -> None:
    result = check_for_updates(settings=AppSettings(update_check_enabled=False))

    assert result.update_available is False
    assert result.error == "Update checks are disabled by configuration."


def test_apply_update_dry_run_returns_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "modelmeter.core.updater._resolve_install_spec",
        lambda *, version, timeout_seconds: f"https://example.com/modelmeter-{version}.whl",
    )

    spec, command = apply_update(
        settings=AppSettings(),
        version="2026.3.20",
        method="pip",
        dry_run=True,
    )

    assert spec == "https://example.com/modelmeter-2026.3.20.whl"
    assert command[:4] == ["python3", "-m", "pip", "install"]


def test_apply_update_runs_install_command(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "modelmeter.core.updater._resolve_install_spec",
        lambda *, version, timeout_seconds: f"https://example.com/modelmeter-{version}.whl",
    )
    calls: list[list[str]] = []

    def _record(command: list[str]) -> None:
        calls.append(command)

    monkeypatch.setattr("modelmeter.core.updater._run_install_command", _record)

    apply_update(
        settings=AppSettings(),
        version="2026.3.20",
        method="auto",
        dry_run=False,
    )

    assert calls
    assert calls[0][-1].endswith("2026.3.20.whl")
