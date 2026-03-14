from typer.testing import CliRunner
import pytest

from modelmeter.cli.main import app
from modelmeter.common.formatting import format_pricing_source_human, format_usd_human


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

    assert result.exit_code == 0
    assert "--cors" in result.stdout
    assert "--log-level" in result.stdout
    assert "--access-log" in result.stdout
    assert "--no-access-log" in result.stdout


def test_version_flag_prints_runtime_version() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["--version"])

    assert result.exit_code == 0
    assert result.stdout.strip()


def test_update_check_command_json_output(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()

    class _Result:
        def model_dump_json(self, *, indent: int) -> str:
            return '{"update_available": true, "latest_version": "2026.3.20"}'

    monkeypatch.setattr("modelmeter.cli.main.check_for_updates", lambda *, settings: _Result())

    result = runner.invoke(app, ["update", "check", "--json"])
    assert result.exit_code == 0
    assert '"update_available": true' in result.stdout


def test_update_apply_dry_run_command(monkeypatch: pytest.MonkeyPatch) -> None:
    runner = CliRunner()
    monkeypatch.setattr(
        "modelmeter.cli.main.apply_update",
        lambda *, settings, version, method, dry_run: (
            "https://example.com/modelmeter.whl",
            ["python3", "-m", "pip", "install", "--user", "--upgrade", "https://example.com/modelmeter.whl"],
        ),
    )

    result = runner.invoke(app, ["update", "apply", "--dry-run"])
    assert result.exit_code == 0
    assert "Dry run complete" in result.stdout
