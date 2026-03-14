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


def test_providers_help_command_runs() -> None:
    runner = CliRunner()
    result = runner.invoke(app, ["providers", "--help"])

    assert result.exit_code == 0
    assert "top provider usage" in result.stdout.lower()
