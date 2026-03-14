"""CLI entrypoint for ModelMeter."""

from __future__ import annotations

import os
import time
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import typer
import uvicorn
from rich.columns import Columns
from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

from modelmeter.api.app import create_app
from modelmeter.common.formatting import (
    format_pricing_source_human,
    format_tokens_human,
    format_usd_human,
)
from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import (
    get_daily,
    get_model_detail,
    get_models,
    get_projects,
    get_providers,
    get_summary,
)
from modelmeter.core.doctor import DoctorReport, generate_doctor_report
from modelmeter.core.live import get_live_snapshot
from modelmeter.core.models import (
    DailyResponse,
    LiveSnapshotResponse,
    ModelDetailResponse,
    ModelsResponse,
    ProjectsResponse,
    ProvidersResponse,
    SummaryResponse,
    TokenUsage,
)

app = typer.Typer(
    add_completion=False,
    no_args_is_help=True,
    help="ModelMeter: OpenCode usage analytics for terminal and web.",
)


def _print_version_and_exit(value: bool) -> None:
    if not value:
        return
    typer.echo(AppSettings().app_runtime_version)
    raise typer.Exit()


@app.callback()
def callback(
    version: Annotated[
        bool,
        typer.Option(
            "--version",
            callback=_print_version_and_exit,
            is_eager=True,
            help="Print runtime version and exit.",
        ),
    ] = False,
) -> None:
    """ModelMeter command group."""


@app.command()
def info() -> None:
    """Print current app/runtime settings."""
    settings = AppSettings()
    console = Console()
    console.print(f"[bold]ModelMeter[/bold] v{settings.app_runtime_version}")
    console.print(f"Data directory: {settings.opencode_data_dir}")


def _render_doctor_report(console: Console, report: DoctorReport) -> None:
    console.print(f"[bold]ModelMeter[/bold] v{report.app_version}")
    console.print(f"OpenCode data dir: {report.opencode_data_dir}")
    console.print(f"Selected source: [bold]{report.selected_source}[/bold]")

    sqlite_table = Table(title="SQLite Diagnostics")
    sqlite_table.add_column("Field")
    sqlite_table.add_column("Value")
    sqlite_table.add_row("DB Path", report.sqlite.db_path)
    sqlite_table.add_row("Exists", str(report.sqlite.exists))
    sqlite_table.add_row("Can Connect", str(report.sqlite.can_connect))
    sqlite_table.add_row("SQLite Version", report.sqlite.sqlite_version or "n/a")
    sqlite_table.add_row(
        "Missing Tables",
        ", ".join(report.sqlite.missing_tables) if report.sqlite.missing_tables else "none",
    )
    sqlite_table.add_row(
        "Schema Errors",
        str(report.sqlite.missing_columns) if report.sqlite.missing_columns else "none",
    )
    sqlite_table.add_row("Error", report.sqlite.error or "none")
    console.print(sqlite_table)

    legacy_table = Table(title="Legacy Message Storage")
    legacy_table.add_column("Field")
    legacy_table.add_column("Value")
    legacy_table.add_row("Candidates", str(len(report.legacy.candidate_dirs)))
    legacy_table.add_row("Existing", str(len(report.legacy.existing_dirs)))
    legacy_table.add_row(
        "Directories",
        "\n".join(report.legacy.existing_dirs) if report.legacy.existing_dirs else "none",
    )
    console.print(legacy_table)


def _render_usage_table(console: Console, usage: TokenUsage, title: str) -> None:
    table = Table(title=title)
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Input", format_tokens_human(usage.input_tokens))
    table.add_row("Output", format_tokens_human(usage.output_tokens))
    table.add_row("Cache Read", format_tokens_human(usage.cache_read_tokens))
    table.add_row("Cache Write", format_tokens_human(usage.cache_write_tokens))
    table.add_row("Total", format_tokens_human(usage.total_tokens))
    console.print(table)


def _render_summary(console: Console, summary: SummaryResponse) -> None:
    window = f"last {summary.window_days} day(s)" if summary.window_days else "all time"
    console.print(f"[bold]Summary[/bold] ({window})")
    console.print(f"Sessions: {summary.total_sessions}")
    if summary.cost_usd is None:
        console.print("Cost: n/a (no pricing file found)")
    else:
        console.print(f"Cost: {format_usd_human(summary.cost_usd)}")
        if summary.pricing_source:
            console.print(f"Pricing source: {format_pricing_source_human(summary.pricing_source)}")
    _render_usage_table(console, summary.usage, "Token Usage")


def _render_daily(console: Console, response: DailyResponse) -> None:
    window = f"last {response.window_days} day(s)" if response.window_days else "all time"
    console.print(f"[bold]Daily Usage[/bold] ({window})")

    daily_table = Table(title="Daily Breakdown")
    daily_table.add_column("Day")
    daily_table.add_column("Sessions", justify="right")
    daily_table.add_column("Input", justify="right")
    daily_table.add_column("Output", justify="right")
    daily_table.add_column("Cache Read", justify="right")
    daily_table.add_column("Cache Write", justify="right")
    daily_table.add_column("Cost (USD)", justify="right")
    daily_table.add_column("Total", justify="right")

    for row in response.daily:
        daily_table.add_row(
            row.day.isoformat(),
            str(row.total_sessions),
            format_tokens_human(row.usage.input_tokens),
            format_tokens_human(row.usage.output_tokens),
            format_tokens_human(row.usage.cache_read_tokens),
            format_tokens_human(row.usage.cache_write_tokens),
            format_usd_human(row.cost_usd) if row.cost_usd is not None else "n/a",
            format_tokens_human(row.usage.total_tokens),
        )

    console.print(daily_table)
    console.print(f"Sessions: {response.total_sessions}")
    if response.total_cost_usd is None:
        console.print("Cost: n/a (no pricing file found)")
    else:
        console.print(f"Cost: {format_usd_human(response.total_cost_usd)}")
        if response.pricing_source:
            console.print(f"Pricing source: {format_pricing_source_human(response.pricing_source)}")
    _render_usage_table(console, response.totals, "Totals")


def _render_models(console: Console, response: ModelsResponse) -> None:
    window = f"last {response.window_days} day(s)" if response.window_days else "all time"
    console.print(f"[bold]Models[/bold] ({window})")
    console.print(f"Sessions: {response.total_sessions}")
    if response.total_cost_usd is None:
        console.print("Cost: n/a (no pricing file found)")
    else:
        console.print(f"Cost: {format_usd_human(response.total_cost_usd)}")
        if response.pricing_source:
            console.print(f"Pricing source: {format_pricing_source_human(response.pricing_source)}")
    console.print(
        f"Priced models: {response.priced_models} | Unpriced models: {response.unpriced_models}"
    )

    table = Table(title="Model Breakdown")
    table.add_column("Model")
    table.add_column("Sessions", justify="right")
    table.add_column("Msgs", justify="right")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cache Read", justify="right")
    table.add_column("Cache Write", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Cost", justify="right")

    for model in response.models:
        table.add_row(
            model.model_id,
            str(model.total_sessions),
            str(model.total_interactions),
            format_tokens_human(model.usage.input_tokens),
            format_tokens_human(model.usage.output_tokens),
            format_tokens_human(model.usage.cache_read_tokens),
            format_tokens_human(model.usage.cache_write_tokens),
            format_tokens_human(model.usage.total_tokens),
            format_usd_human(model.cost_usd) if model.cost_usd is not None else "n/a",
        )

    console.print(table)


def _render_model_detail(console: Console, response: ModelDetailResponse) -> None:
    window = f"last {response.window_days} day(s)" if response.window_days else "all time"
    console.print(f"[bold]Model Detail[/bold] ({window})")
    console.print(f"Model: {response.model_id}")
    console.print(f"Sessions: {response.total_sessions}")
    console.print(f"Messages: {response.total_interactions}")
    if response.cost_usd is None:
        console.print("Cost: n/a (no pricing for this model)")
    else:
        console.print(f"Cost: {format_usd_human(response.cost_usd)}")
        if response.pricing_source:
            console.print(f"Pricing source: {format_pricing_source_human(response.pricing_source)}")

    _render_usage_table(console, response.usage, "Model Totals")

    daily_table = Table(title="Daily Model Breakdown")
    daily_table.add_column("Day")
    daily_table.add_column("Sessions", justify="right")
    daily_table.add_column("Input", justify="right")
    daily_table.add_column("Output", justify="right")
    daily_table.add_column("Cache Read", justify="right")
    daily_table.add_column("Cache Write", justify="right")
    daily_table.add_column("Cost (USD)", justify="right")
    daily_table.add_column("Total", justify="right")

    for row in response.daily:
        daily_table.add_row(
            row.day.isoformat(),
            str(row.total_sessions),
            format_tokens_human(row.usage.input_tokens),
            format_tokens_human(row.usage.output_tokens),
            format_tokens_human(row.usage.cache_read_tokens),
            format_tokens_human(row.usage.cache_write_tokens),
            format_usd_human(row.cost_usd) if row.cost_usd is not None else "n/a",
            format_tokens_human(row.usage.total_tokens),
        )

    console.print(daily_table)


def _render_projects(console: Console, response: ProjectsResponse) -> None:
    window = f"last {response.window_days} day(s)" if response.window_days else "all time"
    console.print(f"[bold]Projects[/bold] ({window})")
    console.print(f"Sessions: {response.total_sessions}")
    if response.total_cost_usd is None:
        console.print("Cost: n/a (no pricing file found)")
    else:
        console.print(f"Cost: {format_usd_human(response.total_cost_usd)}")
        if response.pricing_source:
            console.print(f"Pricing source: {format_pricing_source_human(response.pricing_source)}")

    table = Table(title="Project Breakdown")
    table.add_column("Project")
    table.add_column("Sessions", justify="right")
    table.add_column("Msgs", justify="right")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cache Read", justify="right")
    table.add_column("Cache Write", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Cost", justify="right")

    for project in response.projects:
        label = project.project_name
        if project.project_path:
            label = f"{project.project_name}\n{project.project_path}"
        table.add_row(
            label,
            str(project.total_sessions),
            str(project.total_interactions),
            format_tokens_human(project.usage.input_tokens),
            format_tokens_human(project.usage.output_tokens),
            format_tokens_human(project.usage.cache_read_tokens),
            format_tokens_human(project.usage.cache_write_tokens),
            format_tokens_human(project.usage.total_tokens),
            format_usd_human(project.cost_usd) if project.cost_usd is not None else "n/a",
        )

    console.print(table)


def _render_providers(console: Console, response: ProvidersResponse) -> None:
    window = f"last {response.window_days} day(s)" if response.window_days else "all time"
    console.print(f"[bold]Providers[/bold] ({window})")
    console.print(f"Sessions: {response.total_sessions}")
    if response.total_cost_usd is None:
        console.print("Cost: n/a (no pricing file found)")
    else:
        console.print(f"Cost: {format_usd_human(response.total_cost_usd)}")
        if response.pricing_source:
            console.print(f"Pricing source: {format_pricing_source_human(response.pricing_source)}")

    table = Table(title="Provider Breakdown")
    table.add_column("Provider")
    table.add_column("Models", justify="right")
    table.add_column("Msgs", justify="right")
    table.add_column("Input", justify="right")
    table.add_column("Output", justify="right")
    table.add_column("Cache Read", justify="right")
    table.add_column("Cache Write", justify="right")
    table.add_column("Total", justify="right")
    table.add_column("Cost", justify="right")

    for provider in response.providers:
        table.add_row(
            provider.provider,
            str(provider.total_models),
            str(provider.total_interactions),
            format_tokens_human(provider.usage.input_tokens),
            format_tokens_human(provider.usage.output_tokens),
            format_tokens_human(provider.usage.cache_read_tokens),
            format_tokens_human(provider.usage.cache_write_tokens),
            format_tokens_human(provider.usage.total_tokens),
            format_usd_human(provider.cost_usd) if provider.cost_usd is not None else "n/a",
        )

    console.print(table)


def _signed_tokens(value: int) -> str:
    if value == 0:
        return "0"
    sign = "+" if value > 0 else "-"
    return f"{sign}{format_tokens_human(abs(value))}"


def _signed_usd(value: float) -> str:
    if value == 0:
        return "$0.000000"
    sign = "+" if value > 0 else "-"
    return f"{sign}{format_usd_human(abs(value))}"


def _render_live_snapshot(
    snapshot: LiveSnapshotResponse,
    previous: LiveSnapshotResponse | None,
) -> Columns:
    interactions_delta = 0
    sessions_delta = 0
    usage_delta = TokenUsage()
    cost_delta = 0.0
    if previous is not None:
        interactions_delta = snapshot.total_interactions - previous.total_interactions
        sessions_delta = snapshot.total_sessions - previous.total_sessions
        usage_delta = TokenUsage(
            input_tokens=snapshot.usage.input_tokens - previous.usage.input_tokens,
            output_tokens=snapshot.usage.output_tokens - previous.usage.output_tokens,
            cache_read_tokens=snapshot.usage.cache_read_tokens - previous.usage.cache_read_tokens,
            cache_write_tokens=snapshot.usage.cache_write_tokens
            - previous.usage.cache_write_tokens,
        )
        if snapshot.cost_usd is not None and previous.cost_usd is not None:
            cost_delta = snapshot.cost_usd - previous.cost_usd

    generated_at = datetime.fromtimestamp(snapshot.generated_at_ms / 1000).strftime("%H:%M:%S")
    active_text = "none"
    if snapshot.active_session is not None:
        status = "active" if snapshot.active_session.is_active else "idle"
        title = snapshot.active_session.title or snapshot.active_session.session_id
        active_text = f"{title} ({status})"

    activity_panel = Panel(
        "\n".join(
            [
                f"Updated: {generated_at}",
                f"Window: {snapshot.window_minutes}m",
                f"Token Source: {snapshot.token_source}",
                f"Active Session: {active_text}",
                "Interactions: "
                f"{snapshot.total_interactions} ({_signed_tokens(interactions_delta)})",
                f"Sessions: {snapshot.total_sessions} ({_signed_tokens(sessions_delta)})",
            ]
        ),
        title="Activity",
    )

    usage_lines = [
        "Input: "
        f"{format_tokens_human(snapshot.usage.input_tokens)} "
        f"({_signed_tokens(usage_delta.input_tokens)})",
        "Output: "
        f"{format_tokens_human(snapshot.usage.output_tokens)} "
        f"({_signed_tokens(usage_delta.output_tokens)})",
        "Cache Read: "
        f"{format_tokens_human(snapshot.usage.cache_read_tokens)} "
        f"({_signed_tokens(usage_delta.cache_read_tokens)})",
        "Cache Write: "
        f"{format_tokens_human(snapshot.usage.cache_write_tokens)} "
        f"({_signed_tokens(usage_delta.cache_write_tokens)})",
        "Total: "
        f"{format_tokens_human(snapshot.usage.total_tokens)} "
        f"({_signed_tokens(usage_delta.total_tokens)})",
    ]
    if snapshot.cost_usd is None:
        usage_lines.append("Cost: n/a")
    else:
        usage_lines.append(
            f"Cost: {format_usd_human(snapshot.cost_usd)} ({_signed_usd(cost_delta)})"
        )

    usage_panel = Panel("\n".join(usage_lines), title="Rolling Usage")

    model_table = Table(title="Top Models")
    model_table.add_column("Model")
    model_table.add_column("Tokens", justify="right")
    model_table.add_column("Msgs", justify="right")
    model_table.add_column("Cost", justify="right")
    for row in snapshot.top_models:
        model_table.add_row(
            row.model_id,
            format_tokens_human(row.usage.total_tokens),
            str(row.total_interactions),
            format_usd_human(row.cost_usd) if row.cost_usd is not None else "n/a",
        )

    tool_table = Table(title="Top Tools")
    tool_table.add_column("Tool")
    tool_table.add_column("Calls", justify="right")
    for row in snapshot.top_tools:
        tool_table.add_row(row.tool_name, str(row.total_calls))

    return Columns(
        [
            Columns([activity_panel, usage_panel]),
            Columns([model_table, tool_table]),
        ],
        expand=True,
    )


@app.command()
def doctor(
    db_path: Annotated[
        Path | None,
        typer.Option(
            "--db-path",
            help="Override OpenCode SQLite path for diagnostics.",
        ),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print diagnostics as JSON.",
        ),
    ] = False,
) -> None:
    """Check OpenCode data source and schema compatibility."""
    settings = AppSettings()
    report = generate_doctor_report(settings=settings, db_path_override=db_path)

    if json_output:
        typer.echo(report.model_dump_json(indent=2))
        return

    _render_doctor_report(Console(), report)


@app.command()
def summary(
    days: Annotated[
        int | None,
        typer.Option(
            "--days",
            min=1,
            help="Limit aggregation to the last N days.",
        ),
    ] = 7,
    db_path: Annotated[
        Path | None,
        typer.Option(
            "--db-path",
            help="Override OpenCode SQLite path.",
        ),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option(
            "--pricing-file",
            help="Path to models pricing JSON file.",
        ),
    ] = None,
    token_source: Annotated[
        Literal["auto", "message", "steps"],
        typer.Option(
            "--token-source",
            help="Token aggregation source: auto, message, or steps.",
        ),
    ] = "auto",
    session_source: Annotated[
        Literal["auto", "activity", "session"],
        typer.Option(
            "--session-source",
            help="Session counting source: auto, activity, or session.",
        ),
    ] = "auto",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print summary as JSON.",
        ),
    ] = False,
) -> None:
    """Show aggregate token usage summary."""
    settings = AppSettings()
    result = get_summary(
        settings=settings,
        days=days,
        db_path_override=db_path,
        pricing_file_override=pricing_file,
        token_source=token_source,
        session_count_source=session_source,
    )

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    _render_summary(Console(), result)


@app.command()
def daily(
    days: Annotated[
        int | None,
        typer.Option(
            "--days",
            min=1,
            help="Limit aggregation to the last N days.",
        ),
    ] = 7,
    db_path: Annotated[
        Path | None,
        typer.Option(
            "--db-path",
            help="Override OpenCode SQLite path.",
        ),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option(
            "--pricing-file",
            help="Path to models pricing JSON file.",
        ),
    ] = None,
    token_source: Annotated[
        Literal["auto", "message", "steps"],
        typer.Option(
            "--token-source",
            help="Token aggregation source: auto, message, or steps.",
        ),
    ] = "auto",
    session_source: Annotated[
        Literal["auto", "activity", "session"],
        typer.Option(
            "--session-source",
            help="Session counting source: auto, activity, or session.",
        ),
    ] = "auto",
    json_output: Annotated[
        bool,
        typer.Option(
            "--json",
            help="Print daily usage as JSON.",
        ),
    ] = False,
) -> None:
    """Show daily token usage breakdown."""
    settings = AppSettings()
    result = get_daily(
        settings=settings,
        days=days,
        db_path_override=db_path,
        pricing_file_override=pricing_file,
        token_source=token_source,
        session_count_source=session_source,
    )

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    _render_daily(Console(), result)


@app.command()
def models(
    days: Annotated[
        int | None,
        typer.Option("--days", min=1, help="Limit aggregation to the last N days."),
    ] = 7,
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, help="Show top N models."),
    ] = 20,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Override OpenCode SQLite path."),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option("--pricing-file", help="Path to models pricing JSON file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print models usage as JSON."),
    ] = False,
) -> None:
    """Show top model usage breakdown."""
    settings = AppSettings()
    result = get_models(
        settings=settings,
        days=days,
        db_path_override=db_path,
        pricing_file_override=pricing_file,
        limit=limit,
    )

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    _render_models(Console(), result)


@app.command(name="model")
def model_detail(
    model_id: Annotated[str, typer.Argument(help="Model ID, eg openai/gpt-5")],
    days: Annotated[
        int | None,
        typer.Option("--days", min=1, help="Limit aggregation to the last N days."),
    ] = 7,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Override OpenCode SQLite path."),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option("--pricing-file", help="Path to models pricing JSON file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print model detail as JSON."),
    ] = False,
) -> None:
    """Show usage details for a single model."""
    settings = AppSettings()
    try:
        result = get_model_detail(
            settings=settings,
            model_id=model_id,
            days=days,
            db_path_override=db_path,
            pricing_file_override=pricing_file,
        )
    except RuntimeError as exc:
        typer.echo(f"Error: {exc}")
        raise typer.Exit(code=1) from None

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    _render_model_detail(Console(), result)


@app.command()
def projects(
    days: Annotated[
        int | None,
        typer.Option("--days", min=1, help="Limit aggregation to the last N days."),
    ] = 7,
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, help="Show top N projects."),
    ] = 20,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Override OpenCode SQLite path."),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option("--pricing-file", help="Path to models pricing JSON file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print projects usage as JSON."),
    ] = False,
) -> None:
    """Show top project usage breakdown."""
    settings = AppSettings()
    result = get_projects(
        settings=settings,
        days=days,
        db_path_override=db_path,
        pricing_file_override=pricing_file,
        limit=limit,
    )

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    _render_projects(Console(), result)


@app.command()
def providers(
    days: Annotated[
        int | None,
        typer.Option("--days", min=1, help="Limit aggregation to the last N days."),
    ] = 7,
    limit: Annotated[
        int,
        typer.Option("--limit", min=1, help="Show top N providers."),
    ] = 20,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Override OpenCode SQLite path."),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option("--pricing-file", help="Path to models pricing JSON file."),
    ] = None,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print provider usage as JSON."),
    ] = False,
) -> None:
    """Show top provider usage breakdown."""
    settings = AppSettings()
    result = get_providers(
        settings=settings,
        days=days,
        db_path_override=db_path,
        pricing_file_override=pricing_file,
        limit=limit,
    )

    if json_output:
        typer.echo(result.model_dump_json(indent=2))
        return

    _render_providers(Console(), result)


@app.command()
def live(
    interval: Annotated[
        float,
        typer.Option("--interval", min=0.5, help="Refresh interval in seconds."),
    ] = 3.0,
    window_minutes: Annotated[
        int,
        typer.Option("--window-minutes", min=1, help="Rolling window size in minutes."),
    ] = 60,
    token_source: Annotated[
        Literal["auto", "message", "steps"],
        typer.Option("--token-source", help="Token aggregation source for live mode."),
    ] = "auto",
    models_limit: Annotated[
        int,
        typer.Option("--models-limit", min=1, help="Number of models to show."),
    ] = 5,
    tools_limit: Annotated[
        int,
        typer.Option("--tools-limit", min=1, help="Number of tools to show."),
    ] = 8,
    db_path: Annotated[
        Path | None,
        typer.Option("--db-path", help="Override OpenCode SQLite path."),
    ] = None,
    pricing_file: Annotated[
        Path | None,
        typer.Option("--pricing-file", help="Path to models pricing JSON file."),
    ] = None,
    once: Annotated[
        bool,
        typer.Option("--once", help="Capture one snapshot and exit."),
    ] = False,
    json_output: Annotated[
        bool,
        typer.Option("--json", help="Print live snapshot as JSON."),
    ] = False,
) -> None:
    """Show rolling live activity dashboard."""
    settings = AppSettings()

    def get_snapshot() -> LiveSnapshotResponse:
        return get_live_snapshot(
            settings=settings,
            window_minutes=window_minutes,
            db_path_override=db_path,
            pricing_file_override=pricing_file,
            token_source=token_source,
            models_limit=models_limit,
            tools_limit=tools_limit,
        )

    snapshot = get_snapshot()
    if once:
        if json_output:
            typer.echo(snapshot.model_dump_json(indent=2))
            return
        Console().print(_render_live_snapshot(snapshot, None))
        return

    if json_output:
        typer.echo("Error: --json is only supported with --once")
        raise typer.Exit(code=1)

    previous: LiveSnapshotResponse | None = None
    with Live(
        _render_live_snapshot(snapshot, previous), refresh_per_second=4, screen=False
    ) as live_view:
        previous = snapshot
        try:
            while True:
                time.sleep(interval)
                snapshot = get_snapshot()
                live_view.update(_render_live_snapshot(snapshot, previous))
                previous = snapshot
        except KeyboardInterrupt:
            return


@app.command()
def serve(
    port: Annotated[
        int,
        typer.Option("--port", help="Port to listen on"),
    ] = 8000,
    host: Annotated[
        str,
        typer.Option("--host", help="Host to listen on"),
    ] = "127.0.0.1",
    log_level: Annotated[
        Literal["debug", "info", "warning", "error", "critical"],
        typer.Option("--log-level", help="Server log verbosity."),
    ] = "info",
    access_log: Annotated[
        bool,
        typer.Option("--access-log/--no-access-log", help="Enable request access logs."),
    ] = True,
    cors: Annotated[
        list[str] | None,
        typer.Option(
            "--cors",
            help="Additional browser origin to allow (repeatable).",
        ),
    ] = None,
) -> None:
    """Run the web dashboard server."""
    server_password = os.getenv("MODELMETER_SERVER_PASSWORD")
    server_username = os.getenv("MODELMETER_SERVER_USERNAME") or "modelmeter"
    app_instance = create_app(
        extra_cors_origins=cors,
        server_username=server_username,
        server_password=server_password,
    )

    typer.echo(f"Starting server at http://{host}:{port}")
    uvicorn.run(
        app_instance,
        host=host,
        port=port,
        log_level=log_level,
        access_log=access_log,
    )


def main() -> None:
    """Run the Typer CLI."""
    app()
