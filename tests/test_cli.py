import re
from pathlib import Path

import pytest
from typer.testing import CliRunner

import modelmeter.cli.main as cli_main_module
from modelmeter.cli.main import app
from modelmeter.common.formatting import format_pricing_source_human, format_usd_human
from modelmeter.config.settings import AppSettings
from modelmeter.core.models import UpdateCheckResponse


def _strip_ansi(text: str) -> str:
    return re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", text)


def test_info_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["info"])

    assert result.exit_code == 0
    assert "ModelMeter" in result.stdout


def test_format_usd_humanized_for_large_values() -> None:
    assert format_usd_human(12_438.221) == "$12.4K ($12,438.221000)"


def test_format_pricing_source_humanized() -> None:
    assert (
        format_pricing_source_human(
            "models.dev cache (/Users/slothpro/.cache/modelmeter/models_dev_api.json)"
        )
        == "models.dev (cached)"
    )


def test_serve_help_includes_cors_option() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["serve", "--help"])
    help_text = _strip_ansi(result.stdout)

    assert result.exit_code == 0
    assert "--cors" in help_text
    assert "--log-level" in help_text
    assert "--access-log" in help_text
    assert "--no-access-log" in help_text


def test_version_flag_prints_runtime_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip()


def test_sources_add_list_and_remove(tmp_path: Path) -> None:
    runner = CliRunner()
    registry_path = tmp_path / "sources.json"
    env = {"MODELMETER_SOURCE_REGISTRY_FILE": str(registry_path)}

    add_result = runner.invoke(
        app,
        ["sources", "add-sqlite", "local-main", str(tmp_path / "opencode.db")],
        env=env,
    )
    assert add_result.exit_code == 0

    list_result = runner.invoke(app, ["sources", "list", "--json"], env=env)
    assert list_result.exit_code == 0
    assert '"source_id": "local-main"' in list_result.stdout

    remove_result = runner.invoke(app, ["sources", "remove", "local-main"], env=env)
    assert remove_result.exit_code == 0


def test_sources_check_reports_missing_sqlite_path(tmp_path: Path) -> None:
    runner = CliRunner()
    registry_path = tmp_path / "sources.json"
    env = {"MODELMETER_SOURCE_REGISTRY_FILE": str(registry_path)}

    runner.invoke(
        app,
        ["sources", "add-sqlite", "missing-db", str(tmp_path / "does-not-exist.db")],
        env=env,
    )

    result = runner.invoke(app, ["sources", "check", "--json"], env=env)
    assert result.exit_code == 0
    assert '"source_id": "missing-db"' in result.stdout
    assert '"is_reachable": false' in result.stdout

def test_update_check_command_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()

    def _mock_check_for_updates(*, settings: AppSettings) -> UpdateCheckResponse:
        _ = settings
        return UpdateCheckResponse(
            current_version="2026.3.16",
            latest_version="2026.3.20",
            update_available=True,
            checked_at_ms=1,
        )

    monkeypatch.setattr(cli_main_module, "check_for_updates", _mock_check_for_updates)

    result = runner.invoke(app, ["update", "check", "--json"])
    assert result.exit_code == 0
    assert '"update_available": true' in result.stdout


def test_update_apply_dry_run_command(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()

    def _mock_apply_update(
        *,
        settings: AppSettings,
        version: str | None,
        method: str,
        dry_run: bool,
    ) -> tuple[str, list[str]]:
        _ = (settings, version, method, dry_run)
        return (
            "https://example.com/modelmeter.whl",
            [
                "python3",
                "-m",
                "pip",
                "install",
                "--user",
                "--upgrade",
                "https://example.com/modelmeter.whl",
            ],
        )

    monkeypatch.setattr(cli_main_module, "apply_update", _mock_apply_update)

    result = runner.invoke(app, ["update", "apply", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run complete" in result.stdout
