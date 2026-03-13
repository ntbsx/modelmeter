"""Analytics services for summary and daily usage."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Literal

from modelmeter.config.settings import AppSettings
from modelmeter.core.doctor import generate_doctor_report
from modelmeter.core.models import (
    DailyResponse,
    DailyUsage,
    ModelDetailResponse,
    ModelsResponse,
    ModelUsage,
    ProjectsResponse,
    ProjectUsage,
    SummaryResponse,
    TokenUsage,
)
from modelmeter.core.pricing import calculate_usage_cost, load_pricing_book
from modelmeter.data.sqlite_usage_repository import SQLiteUsageRepository
from modelmeter.data.storage import resolve_storage_paths


def _token_usage_from_row(row: sqlite3.Row) -> TokenUsage:
    mapping = dict(row)  # sqlite3.Row behaves like a mapping
    return TokenUsage(
        input_tokens=int(mapping.get("input_tokens", 0)),
        output_tokens=int(mapping.get("output_tokens", 0)),
        cache_read_tokens=int(mapping.get("cache_read_tokens", mapping.get("cache_read", 0))),
        cache_write_tokens=int(mapping.get("cache_write_tokens", mapping.get("cache_write", 0))),
    )


def _resolve_sqlite_path(settings: AppSettings, db_path_override: Path | None = None) -> Path:
    report = generate_doctor_report(settings=settings, db_path_override=db_path_override)
    if report.selected_source != "sqlite":
        raise RuntimeError(
            "SQLite data source is unavailable or incompatible. "
            "Run `modelmeter doctor` for details."
        )
    paths = resolve_storage_paths(settings, db_path_override=db_path_override)
    return paths.sqlite_db_path


def get_summary(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
) -> SummaryResponse:
    """Return summary usage totals."""
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    resolved_source = repository.resolve_token_source(days=days, token_source=token_source)
    resolved_session_source = repository.resolve_session_count_source(
        days=days,
        session_count_source=session_count_source,
    )

    if resolved_source == "steps":
        row = repository.fetch_summary_steps(days=days)
    else:
        row = repository.fetch_summary(days=days)

    if resolved_session_source == "session":
        total_sessions = repository.fetch_session_count(days=days)
    else:
        total_sessions = int(row["total_sessions"])
    model_rows = repository.fetch_model_usage(days=days)

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    cost_usd: float | None = None
    if pricing_book:
        total_cost = 0.0
        for model_row in model_rows:
            model_id = str(model_row["model_id"])
            pricing = pricing_book.get(model_id)
            if pricing is None:
                continue
            total_cost += calculate_usage_cost(_token_usage_from_row(model_row), pricing)
        cost_usd = round(total_cost, 8)

    return SummaryResponse(
        usage=_token_usage_from_row(row),
        total_sessions=total_sessions,
        window_days=days,
        cost_usd=cost_usd,
        pricing_source=pricing_source,
    )


def get_daily(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
) -> DailyResponse:
    """Return daily usage time-series and totals."""
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    resolved_source = repository.resolve_token_source(days=days, token_source=token_source)
    resolved_session_source = repository.resolve_session_count_source(
        days=days,
        session_count_source=session_count_source,
    )
    if resolved_source == "steps":
        rows = repository.fetch_daily_steps(days=days)
        summary_row = repository.fetch_summary_steps(days=days)
    else:
        rows = repository.fetch_daily(days=days)
        summary_row = repository.fetch_summary(days=days)

    daily_session_counts = repository.fetch_daily_session_counts(days=days)
    if resolved_session_source == "session":
        total_sessions = repository.fetch_session_count(days=days)
    else:
        total_sessions = int(summary_row["total_sessions"])

    daily_model_rows = repository.fetch_daily_model_usage(days=days)

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    daily_cost_map: dict[str, float] = {}
    total_cost_usd: float | None = None
    if pricing_book:
        total_cost_usd = 0.0
        for model_row in daily_model_rows:
            model_id = str(model_row["model_id"])
            pricing = pricing_book.get(model_id)
            if pricing is None:
                continue

            day_key = str(model_row["day"])
            cost = calculate_usage_cost(_token_usage_from_row(model_row), pricing)
            daily_cost_map[day_key] = daily_cost_map.get(day_key, 0.0) + cost
            total_cost_usd += cost

        total_cost_usd = round(total_cost_usd, 8)

    daily_rows: list[DailyUsage] = []
    totals = _token_usage_from_row(summary_row)

    for row in rows:
        usage = _token_usage_from_row(row)
        parsed_day = date.fromisoformat(str(row["day"]))
        if resolved_session_source == "session":
            sessions = daily_session_counts.get(parsed_day.isoformat(), 0)
        else:
            sessions = int(row["total_sessions"])

        daily_rows.append(
            DailyUsage(
                day=parsed_day,
                usage=usage,
                total_sessions=sessions,
                cost_usd=round(daily_cost_map[parsed_day.isoformat()], 8)
                if parsed_day.isoformat() in daily_cost_map
                else None,
            )
        )

    return DailyResponse(
        window_days=days,
        totals=totals,
        total_sessions=total_sessions,
        total_cost_usd=total_cost_usd,
        pricing_source=pricing_source,
        daily=daily_rows,
    )


def get_models(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    limit: int = 20,
) -> ModelsResponse:
    """Return top model usage aggregates."""
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    rows = repository.fetch_model_usage_detail(days=days)
    summary_row = repository.fetch_summary(days=days)
    total_sessions = repository.fetch_session_count(days=days)

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    usage_rows: list[ModelUsage] = []
    total_cost_usd: float | None = 0.0 if pricing_book else None
    priced_models = 0

    for row in rows:
        model_id = str(row["model_id"])
        usage = _token_usage_from_row(row)
        pricing = pricing_book.get(model_id)

        cost_usd: float | None = None
        has_pricing = pricing is not None
        if pricing is not None:
            priced_models += 1
            cost_usd = round(calculate_usage_cost(usage, pricing), 8)
            if total_cost_usd is not None:
                total_cost_usd += cost_usd

        usage_rows.append(
            ModelUsage(
                model_id=model_id,
                usage=usage,
                total_sessions=int(row["total_sessions"]),
                total_interactions=int(row["total_interactions"]),
                cost_usd=cost_usd,
                has_pricing=has_pricing,
            )
        )

    usage_rows.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    if limit > 0:
        usage_rows = usage_rows[:limit]

    return ModelsResponse(
        window_days=days,
        totals=_token_usage_from_row(summary_row),
        total_sessions=total_sessions,
        total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        priced_models=priced_models,
        unpriced_models=max(0, len(rows) - priced_models),
        models=usage_rows,
    )


def get_model_detail(
    *,
    settings: AppSettings,
    model_id: str,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
) -> ModelDetailResponse:
    """Return usage details for one model."""
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)

    requested_model_id = model_id
    row = repository.fetch_model_detail(model_id=requested_model_id, days=days)

    if (row is None or int(row["total_interactions"]) == 0) and "/" in requested_model_id:
        fallback_model_id = requested_model_id.split("/", maxsplit=1)[1]
        fallback_row = repository.fetch_model_detail(model_id=fallback_model_id, days=days)
        if fallback_row is not None and int(fallback_row["total_interactions"]) > 0:
            model_id = fallback_model_id
            row = fallback_row

    if row is None:
        raise RuntimeError(f"No data found for model '{requested_model_id}'.")

    if int(row["total_interactions"]) == 0:
        raise RuntimeError(f"No data found for model '{requested_model_id}'.")

    usage = _token_usage_from_row(row)
    daily_rows = repository.fetch_daily_model_detail(model_id=model_id, days=days)

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )
    pricing = pricing_book.get(model_id)
    cost_usd = round(calculate_usage_cost(usage, pricing), 8) if pricing is not None else None

    daily_usage_rows: list[DailyUsage] = []
    for daily_row in daily_rows:
        day_usage = _token_usage_from_row(daily_row)
        day_cost = (
            round(calculate_usage_cost(day_usage, pricing), 8) if pricing is not None else None
        )
        daily_usage_rows.append(
            DailyUsage(
                day=date.fromisoformat(str(daily_row["day"])),
                usage=day_usage,
                total_sessions=int(daily_row["total_sessions"]),
                cost_usd=day_cost,
            )
        )

    return ModelDetailResponse(
        model_id=model_id,
        window_days=days,
        usage=usage,
        total_sessions=int(row["total_sessions"]),
        total_interactions=int(row["total_interactions"]),
        cost_usd=cost_usd,
        pricing_source=pricing_source,
        daily=daily_usage_rows,
    )


def get_projects(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    limit: int = 20,
) -> ProjectsResponse:
    """Return top project usage aggregates."""
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    rows = repository.fetch_project_usage_detail(days=days)
    summary_row = repository.fetch_summary(days=days)
    total_sessions = repository.fetch_session_count(days=days)

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    project_model_rows = repository.fetch_project_model_usage(days=days)
    project_cost_map: dict[str, float] = {}
    total_cost_usd: float | None = 0.0 if pricing_book else None

    for row in project_model_rows:
        project_id = str(row["project_id"])
        model_id = str(row["model_id"])
        pricing = pricing_book.get(model_id)
        if pricing is None:
            continue
        cost = calculate_usage_cost(_token_usage_from_row(row), pricing)
        project_cost_map[project_id] = project_cost_map.get(project_id, 0.0) + cost
        if total_cost_usd is not None:
            total_cost_usd += cost

    usage_rows: list[ProjectUsage] = []
    for row in rows:
        project_id = str(row["project_id"])
        project_cost = project_cost_map.get(project_id)
        usage_rows.append(
            ProjectUsage(
                project_id=project_id,
                project_name=str(row["project_name"]),
                project_path=str(row["project_path"]) if row["project_path"] is not None else None,
                usage=_token_usage_from_row(row),
                total_sessions=int(row["total_sessions"]),
                total_interactions=int(row["total_interactions"]),
                cost_usd=round(project_cost, 8) if project_cost is not None else None,
                has_pricing=project_cost is not None,
            )
        )

    usage_rows.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    if limit > 0:
        usage_rows = usage_rows[:limit]

    return ProjectsResponse(
        window_days=days,
        totals=_token_usage_from_row(summary_row),
        total_sessions=total_sessions,
        total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        projects=usage_rows,
    )
