from pathlib import Path

from typer.testing import CliRunner

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
