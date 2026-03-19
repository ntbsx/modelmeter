"""Analytics services for summary and daily usage."""

from __future__ import annotations

import sqlite3
from datetime import date
from pathlib import Path
from typing import Any, Literal, cast

from modelmeter.config.settings import AppSettings
from modelmeter.core.doctor import generate_doctor_report
from modelmeter.core.models import (
    DailyResponse,
    DailyUsage,
    ModelDetailResponse,
    ModelsResponse,
    ModelUsage,
    ProjectDetailResponse,
    ProjectSessionUsage,
    ProjectsResponse,
    ProjectUsage,
    ProvidersResponse,
    ProviderUsage,
    SummaryResponse,
    TokenUsage,
)
from modelmeter.core.pricing import calculate_usage_cost, load_pricing_book
from modelmeter.core.providers import provider_from_model_id_and_provider_field
from modelmeter.core.sources import SourceScope, SourceScopeKind
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


def _scope_label(source_scope: SourceScope | None) -> str:
    if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL:
        return "local"
    if source_scope.kind == SourceScopeKind.ALL:
        return "all"
    return f"source:{source_scope.source_id}"


def _merge_daily_rows(
    local_rows: list[DailyUsage], federated_rows: list[DailyUsage]
) -> list[DailyUsage]:
    merged: dict[date, DailyUsage] = {}
    for row in local_rows + federated_rows:
        existing = merged.get(row.day)
        if existing is None:
            merged[row.day] = DailyUsage(
                day=row.day,
                usage=TokenUsage(
                    input_tokens=row.usage.input_tokens,
                    output_tokens=row.usage.output_tokens,
                    cache_read_tokens=row.usage.cache_read_tokens,
                    cache_write_tokens=row.usage.cache_write_tokens,
                ),
                total_sessions=row.total_sessions,
                cost_usd=row.cost_usd,
            )
            continue
        existing.usage.input_tokens += row.usage.input_tokens
        existing.usage.output_tokens += row.usage.output_tokens
        existing.usage.cache_read_tokens += row.usage.cache_read_tokens
        existing.usage.cache_write_tokens += row.usage.cache_write_tokens
        existing.total_sessions += row.total_sessions
        if existing.cost_usd is not None or row.cost_usd is not None:
            existing.cost_usd = round((existing.cost_usd or 0.0) + (row.cost_usd or 0.0), 8)
    return sorted(merged.values(), key=lambda item: item.day)


def _merge_model_rows(
    local_rows: list[ModelUsage], federated_rows: list[ModelUsage]
) -> list[ModelUsage]:
    from modelmeter.core.federation import merge_model_usage

    merged: dict[str, ModelUsage] = {}
    for row in local_rows + federated_rows:
        existing = merged.get(row.model_id)
        if existing is None:
            merged[row.model_id] = row
        else:
            merged[row.model_id] = merge_model_usage(existing, row)
    return sorted(merged.values(), key=lambda item: item.usage.total_tokens, reverse=True)


def _merge_provider_rows(
    local_rows: list[ProviderUsage], federated_rows: list[ProviderUsage]
) -> list[ProviderUsage]:
    from modelmeter.core.federation import merge_provider_usage

    merged: dict[str, ProviderUsage] = {}
    for row in local_rows + federated_rows:
        existing = merged.get(row.provider)
        if existing is None:
            merged[row.provider] = row
        else:
            merged[row.provider] = merge_provider_usage(existing, row)
    return sorted(merged.values(), key=lambda item: item.usage.total_tokens, reverse=True)


def _merge_project_rows(
    local_rows: list[ProjectUsage], federated_rows: list[ProjectUsage]
) -> list[ProjectUsage]:
    from modelmeter.core.federation import merge_project_usage

    merged: dict[str, ProjectUsage] = {}
    for row in local_rows + federated_rows:
        existing = merged.get(row.project_id)
        if existing is None:
            merged[row.project_id] = row
        else:
            merged[row.project_id] = merge_project_usage(existing, row)
    return sorted(merged.values(), key=lambda item: item.usage.total_tokens, reverse=True)


def _paginate_rows[T](rows: list[T], *, offset: int, limit: int) -> list[T]:
    page = rows
    if offset > 0:
        page = page[offset:]
    if limit > 0:
        page = page[:limit]
    return page


def get_summary(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
    source_scope: SourceScope | None = None,
) -> SummaryResponse:
    """Return summary usage totals."""
    from modelmeter.core.federation import execute_summary_federated, merge_token_usage
    from modelmeter.core.sources import SourceScopeKind, get_sources_for_scope

    if source_scope is not None and source_scope.kind == SourceScopeKind.ALL:
        local_failed = False
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_summary_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        try:
            local_result = get_summary(
                settings=settings,
                days=days,
                db_path_override=db_path_override,
                pricing_file_override=pricing_file_override,
                token_source=token_source,
                session_count_source=session_count_source,
                source_scope=None,
            )
            result.usage = merge_token_usage(local_result.usage, result.usage)
            result.total_sessions = local_result.total_sessions + result.total_sessions
            if local_result.cost_usd is not None or result.cost_usd is not None:
                result.cost_usd = (local_result.cost_usd or 0) + (result.cost_usd or 0)
            if local_result.pricing_source:
                result.pricing_source = local_result.pricing_source
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_succeeded = ["local"] + result.sources_succeeded
        except RuntimeError as exc:
            local_failed = True
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_failed = [
                {"source_id": "local", "error": str(exc)}
            ] + result.sources_failed

        if local_failed and not result.sources_succeeded:
            raise RuntimeError(result.sources_failed[0]["error"])
        return result

    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_summary_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        return result

    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)

    if token_source == "auto":
        summary_steps = repository.fetch_summary_steps(days=days)
        if int(summary_steps["total_sessions"]) > 0:
            row = summary_steps
        else:
            row = repository.fetch_summary(days=days)
    elif token_source == "steps":
        row = repository.fetch_summary_steps(days=days)
    else:
        row = repository.fetch_summary(days=days)

    if session_count_source == "auto":
        try:
            total_sessions = repository.fetch_session_count(days=days)
        except sqlite3.Error:
            total_sessions = int(row["total_sessions"])
    elif session_count_source == "session":
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
        source_scope=source_scope.kind.value if source_scope else "local",
        sources_considered=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_succeeded=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_failed=[],
    )


def get_daily(
    *,
    settings: AppSettings,
    days: int | None = None,
    timezone_offset_minutes: int = 0,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
    source_scope: SourceScope | None = None,
) -> DailyResponse:
    """Return daily usage time-series and totals."""
    from modelmeter.core.federation import execute_daily_federated, merge_token_usage
    from modelmeter.core.sources import SourceScopeKind, get_sources_for_scope

    if source_scope is not None and source_scope.kind == SourceScopeKind.ALL:
        local_failed = False
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_daily_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            timezone_offset_minutes=timezone_offset_minutes,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        try:
            local_result = get_daily(
                settings=settings,
                days=days,
                timezone_offset_minutes=timezone_offset_minutes,
                db_path_override=db_path_override,
                pricing_file_override=pricing_file_override,
                token_source=token_source,
                session_count_source=session_count_source,
                source_scope=None,
            )
            result.totals = merge_token_usage(local_result.totals, result.totals)
            result.total_sessions = local_result.total_sessions + result.total_sessions
            if local_result.total_cost_usd is not None or result.total_cost_usd is not None:
                result.total_cost_usd = (local_result.total_cost_usd or 0) + (
                    result.total_cost_usd or 0
                )
            if local_result.pricing_source:
                result.pricing_source = local_result.pricing_source
            result.daily = _merge_daily_rows(local_result.daily, result.daily)
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_succeeded = ["local"] + result.sources_succeeded
        except RuntimeError as exc:
            local_failed = True
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_failed = [
                {"source_id": "local", "error": str(exc)}
            ] + result.sources_failed

        if local_failed and not result.sources_succeeded:
            raise RuntimeError(result.sources_failed[0]["error"])
        return result

    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_daily_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            timezone_offset_minutes=timezone_offset_minutes,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        return result
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    resolved_source = repository.resolve_token_source(days=days, token_source=token_source)
    resolved_session_source = repository.resolve_session_count_source(
        days=days,
        session_count_source=session_count_source,
    )
    if resolved_source == "steps":
        rows = repository.fetch_daily_steps(
            days=days,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        summary_row = repository.fetch_summary_steps(days=days)
    else:
        rows = repository.fetch_daily(days=days, timezone_offset_minutes=timezone_offset_minutes)
        summary_row = repository.fetch_summary(days=days)

    daily_session_counts = repository.fetch_daily_session_counts(
        days=days,
        timezone_offset_minutes=timezone_offset_minutes,
    )
    if resolved_session_source == "session":
        total_sessions = repository.fetch_session_count(days=days)
    else:
        total_sessions = int(summary_row["total_sessions"])

    daily_model_rows = repository.fetch_daily_model_usage(
        days=days,
        timezone_offset_minutes=timezone_offset_minutes,
    )

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
        source_scope=source_scope.kind.value if source_scope else "local",
        sources_considered=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_succeeded=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_failed=[],
    )


def get_models(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    provider: str | None = None,
    offset: int = 0,
    limit: int = 20,
    token_source: str = "auto",
    session_count_source: str = "auto",
    source_scope: SourceScope | None = None,
) -> ModelsResponse:
    """Return top model usage aggregates."""
    from modelmeter.core.federation import execute_models_federated, merge_token_usage
    from modelmeter.core.sources import SourceScopeKind, get_sources_for_scope

    if source_scope is not None and source_scope.kind == SourceScopeKind.ALL:
        local_failed = False
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_models_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            offset=0,
            limit=0,
            provider=provider,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        try:
            local_result = get_models(
                settings=settings,
                days=days,
                db_path_override=db_path_override,
                pricing_file_override=pricing_file_override,
                provider=provider,
                offset=0,
                limit=0,
                token_source=token_source,
                session_count_source=session_count_source,
                source_scope=None,
            )
            result.totals = merge_token_usage(local_result.totals, result.totals)
            result.total_sessions = local_result.total_sessions + result.total_sessions
            if local_result.total_cost_usd is not None or result.total_cost_usd is not None:
                result.total_cost_usd = (local_result.total_cost_usd or 0) + (
                    result.total_cost_usd or 0
                )
            if local_result.pricing_source:
                result.pricing_source = local_result.pricing_source
            merged_rows = _merge_model_rows(local_result.models, result.models)
            result.total_models = len(merged_rows)
            result.priced_models = sum(1 for item in merged_rows if item.has_pricing)
            result.unpriced_models = max(0, result.total_models - result.priced_models)
            result.models = _paginate_rows(merged_rows, offset=offset, limit=limit)
            result.models_offset = offset
            result.models_limit = limit
            result.models_returned = len(result.models)
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_succeeded = ["local"] + result.sources_succeeded
        except RuntimeError as exc:
            local_failed = True
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_failed = [
                {"source_id": "local", "error": str(exc)}
            ] + result.sources_failed

        if local_failed and not result.sources_succeeded:
            raise RuntimeError(result.sources_failed[0]["error"])
        return result

    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_models_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            offset=offset,
            limit=limit,
            provider=provider,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        return result
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    rows = repository.fetch_model_usage_detail(days=days)

    if provider is not None:
        filtered_rows: list[Any] = []
        for row in rows:
            model_id = str(row["model_id"])
            provider_id = row["provider_id"]
            if provider_from_model_id_and_provider_field(model_id, provider_id) == provider:
                filtered_rows.append(row)  # type: ignore
        rows = filtered_rows

        totals = TokenUsage(
            input_tokens=sum(int(cast(Any, r)["input_tokens"]) for r in rows),  # type: ignore
            output_tokens=sum(int(cast(Any, r)["output_tokens"]) for r in rows),  # type: ignore
            cache_read_tokens=sum(int(cast(Any, r)["cache_read"]) for r in rows),  # type: ignore
            cache_write_tokens=sum(int(cast(Any, r)["cache_write"]) for r in rows),  # type: ignore
        )
        total_sessions = sum(int(cast(Any, r)["total_sessions"]) for r in rows)  # type: ignore
    else:
        summary_row = repository.fetch_summary(days=days)
        totals = _token_usage_from_row(summary_row)
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

    total_models = len(usage_rows)

    if offset > 0:
        usage_rows = usage_rows[offset:]
    if limit > 0:
        usage_rows = usage_rows[:limit]

    return ModelsResponse(
        window_days=days,
        models_offset=offset,
        models_limit=limit if limit > 0 else None,
        models_returned=len(usage_rows),
        total_models=total_models,
        totals=totals,
        total_sessions=total_sessions,
        total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        priced_models=priced_models,
        unpriced_models=max(0, len(rows) - priced_models),
        models=usage_rows,
        source_scope=source_scope.kind.value if source_scope else "local",
        sources_considered=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_succeeded=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_failed=[],
    )


def get_providers(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    offset: int = 0,
    limit: int = 20,
    token_source: str = "auto",
    session_count_source: str = "auto",
    source_scope: SourceScope | None = None,
) -> ProvidersResponse:
    """Return usage aggregates grouped by provider."""
    from modelmeter.core.federation import execute_providers_federated, merge_token_usage
    from modelmeter.core.sources import SourceScopeKind, get_sources_for_scope

    if source_scope is not None and source_scope.kind == SourceScopeKind.ALL:
        local_failed = False
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_providers_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            offset=0,
            limit=0,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        try:
            local_result = get_providers(
                settings=settings,
                days=days,
                db_path_override=db_path_override,
                pricing_file_override=pricing_file_override,
                offset=0,
                limit=0,
                token_source=token_source,
                session_count_source=session_count_source,
                source_scope=None,
            )
            result.totals = merge_token_usage(local_result.totals, result.totals)
            result.total_sessions = local_result.total_sessions + result.total_sessions
            if local_result.total_cost_usd is not None or result.total_cost_usd is not None:
                result.total_cost_usd = (local_result.total_cost_usd or 0) + (
                    result.total_cost_usd or 0
                )
            if local_result.pricing_source:
                result.pricing_source = local_result.pricing_source
            merged_rows = _merge_provider_rows(local_result.providers, result.providers)
            result.total_providers = len(merged_rows)
            result.providers = _paginate_rows(merged_rows, offset=offset, limit=limit)
            result.providers_offset = offset
            result.providers_limit = limit
            result.providers_returned = len(result.providers)
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_succeeded = ["local"] + result.sources_succeeded
        except RuntimeError as exc:
            local_failed = True
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_failed = [
                {"source_id": "local", "error": str(exc)}
            ] + result.sources_failed

        if local_failed and not result.sources_succeeded:
            raise RuntimeError(result.sources_failed[0]["error"])
        return result

    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_providers_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            offset=offset,
            limit=limit,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        return result
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)
    model_rows = repository.fetch_model_usage_detail(days=days)
    summary_row = repository.fetch_summary(days=days)
    total_sessions = repository.fetch_session_count(days=days)

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    provider_map: dict[str, ProviderUsage] = {}
    total_cost_usd: float | None = 0.0 if pricing_book else None

    for row in model_rows:
        model_id = str(row["model_id"])
        provider_id = row["provider_id"]
        provider = provider_from_model_id_and_provider_field(model_id, provider_id)
        usage = _token_usage_from_row(row)

        model_cost: float | None = None
        pricing = pricing_book.get(model_id)
        if pricing is not None:
            model_cost = round(calculate_usage_cost(usage, pricing), 8)
            if total_cost_usd is not None:
                total_cost_usd += model_cost

        existing = provider_map.get(provider)
        if existing is None:
            provider_map[provider] = ProviderUsage(
                provider=provider,
                usage=TokenUsage(
                    input_tokens=usage.input_tokens,
                    output_tokens=usage.output_tokens,
                    cache_read_tokens=usage.cache_read_tokens,
                    cache_write_tokens=usage.cache_write_tokens,
                ),
                total_models=1,
                total_interactions=int(row["total_interactions"]),
                cost_usd=model_cost,
                has_pricing=model_cost is not None,
            )
            continue

        existing.usage.input_tokens += usage.input_tokens
        existing.usage.output_tokens += usage.output_tokens
        existing.usage.cache_read_tokens += usage.cache_read_tokens
        existing.usage.cache_write_tokens += usage.cache_write_tokens
        existing.total_models += 1
        existing.total_interactions += int(row["total_interactions"])
        if model_cost is not None:
            existing.has_pricing = True
            if existing.cost_usd is None:
                existing.cost_usd = model_cost
            else:
                existing.cost_usd = round(existing.cost_usd + model_cost, 8)

    provider_rows = sorted(
        provider_map.values(), key=lambda item: item.usage.total_tokens, reverse=True
    )
    total_providers = len(provider_rows)

    if offset > 0:
        provider_rows = provider_rows[offset:]
    if limit > 0:
        provider_rows = provider_rows[:limit]

    return ProvidersResponse(
        window_days=days,
        providers_offset=offset,
        providers_limit=limit if limit > 0 else None,
        providers_returned=len(provider_rows),
        total_providers=total_providers,
        totals=_token_usage_from_row(summary_row),
        total_sessions=total_sessions,
        total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        providers=provider_rows,
        source_scope=source_scope.kind.value if source_scope else "local",
        sources_considered=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_succeeded=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_failed=[],
    )


def get_model_detail(
    *,
    settings: AppSettings,
    model_id: str,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    source_scope: SourceScope | None = None,
) -> ModelDetailResponse:
    """Return usage details for one model."""
    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        raise NotImplementedError("Federated model detail analytics not yet implemented")
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
        provider=provider_from_model_id_and_provider_field(model_id, row["provider_id"]),
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
    offset: int = 0,
    limit: int = 20,
    token_source: str = "auto",
    session_count_source: str = "auto",
    source_scope: SourceScope | None = None,
) -> ProjectsResponse:
    """Return top project usage aggregates."""
    from modelmeter.core.federation import execute_projects_federated, merge_token_usage
    from modelmeter.core.sources import SourceScopeKind, get_sources_for_scope

    if source_scope is not None and source_scope.kind == SourceScopeKind.ALL:
        local_failed = False
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_projects_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            offset=0,
            limit=0,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        try:
            local_result = get_projects(
                settings=settings,
                days=days,
                db_path_override=db_path_override,
                pricing_file_override=pricing_file_override,
                offset=0,
                limit=0,
                token_source=token_source,
                session_count_source=session_count_source,
                source_scope=None,
            )
            result.totals = merge_token_usage(local_result.totals, result.totals)
            result.total_sessions = local_result.total_sessions + result.total_sessions
            if local_result.total_cost_usd is not None or result.total_cost_usd is not None:
                result.total_cost_usd = (local_result.total_cost_usd or 0) + (
                    result.total_cost_usd or 0
                )
            if local_result.pricing_source:
                result.pricing_source = local_result.pricing_source
            merged_rows = _merge_project_rows(local_result.projects, result.projects)
            result.total_projects = len(merged_rows)
            result.projects = _paginate_rows(merged_rows, offset=offset, limit=limit)
            result.projects_offset = offset
            result.projects_limit = limit
            result.projects_returned = len(result.projects)
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_succeeded = ["local"] + result.sources_succeeded
        except RuntimeError as exc:
            local_failed = True
            result.sources_considered = ["local"] + result.sources_considered
            result.sources_failed = [
                {"source_id": "local", "error": str(exc)}
            ] + result.sources_failed

        if local_failed and not result.sources_succeeded:
            raise RuntimeError(result.sources_failed[0]["error"])
        return result

    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        sources, failures = get_sources_for_scope(settings=settings, scope=source_scope)
        result, _ = execute_projects_federated(
            sources,
            failures,
            settings=settings,
            days=days,
            offset=offset,
            limit=limit,
            token_source=token_source,
            session_count_source=session_count_source,
            scope_label=_scope_label(source_scope),
        )
        return result
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
                sources=["local"],
            )
        )

    total_projects = len(usage_rows)

    if offset > 0:
        usage_rows = usage_rows[offset:]
    if limit > 0:
        usage_rows = usage_rows[:limit]

    return ProjectsResponse(
        window_days=days,
        projects_offset=offset,
        projects_limit=limit if limit > 0 else None,
        projects_returned=len(usage_rows),
        total_projects=total_projects,
        totals=_token_usage_from_row(summary_row),
        total_sessions=total_sessions,
        total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        projects=usage_rows,
        source_scope=source_scope.kind.value if source_scope else "local",
        sources_considered=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_succeeded=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_failed=[],
    )


def get_project_detail(
    *,
    settings: AppSettings,
    project_id: str,
    days: int | None = None,
    session_offset: int = 0,
    session_limit: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    source_scope: SourceScope | None = None,
) -> ProjectDetailResponse:
    """Return session-level usage details for one project."""
    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        raise NotImplementedError("Federated project detail analytics not yet implemented")
    sqlite_db_path = _resolve_sqlite_path(settings, db_path_override)
    repository = SQLiteUsageRepository(sqlite_db_path)

    session_rows = repository.fetch_project_session_usage(project_id=project_id, days=days)
    if not session_rows:
        raise RuntimeError(f"No data found for project '{project_id}'.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )
    session_model_rows = repository.fetch_project_session_model_usage(
        project_id=project_id, days=days
    )

    session_cost_map: dict[str, float] = {}
    total_cost_usd: float | None = 0.0 if pricing_book else None
    for row in session_model_rows:
        session_id = str(row["session_id"])
        model_id = str(row["model_id"])
        pricing = pricing_book.get(model_id)
        if pricing is None:
            continue

        cost = calculate_usage_cost(_token_usage_from_row(row), pricing)
        session_cost_map[session_id] = session_cost_map.get(session_id, 0.0) + cost
        if total_cost_usd is not None:
            total_cost_usd += cost

    sessions: list[ProjectSessionUsage] = []
    total_interactions = 0
    aggregate_usage = TokenUsage()
    total_sessions = len(session_rows)

    first_row = session_rows[0]
    project_name = str(first_row["project_name"])
    project_path = str(first_row["project_path"]) if first_row["project_path"] is not None else None

    for row in session_rows:
        session_id = str(row["session_id"])
        usage = _token_usage_from_row(row)
        total_interactions += int(row["total_interactions"])
        aggregate_usage.input_tokens += usage.input_tokens
        aggregate_usage.output_tokens += usage.output_tokens
        aggregate_usage.cache_read_tokens += usage.cache_read_tokens
        aggregate_usage.cache_write_tokens += usage.cache_write_tokens

        session_cost = session_cost_map.get(session_id)
        sessions.append(
            ProjectSessionUsage(
                session_id=session_id,
                title=str(row["title"]) if row["title"] is not None else None,
                directory=str(row["directory"]) if row["directory"] is not None else None,
                last_updated_ms=int(row["last_updated_ms"]),
                usage=usage,
                total_interactions=int(row["total_interactions"]),
                cost_usd=round(session_cost, 8) if session_cost is not None else None,
                has_pricing=session_cost is not None,
            )
        )

    sliced_sessions = sessions[session_offset:]
    if session_limit is not None:
        sliced_sessions = sliced_sessions[:session_limit]

    return ProjectDetailResponse(
        project_id=project_id,
        project_name=project_name,
        project_path=project_path,
        window_days=days,
        usage=aggregate_usage,
        total_sessions=total_sessions,
        sessions_offset=session_offset,
        sessions_limit=session_limit,
        sessions_returned=len(sliced_sessions),
        total_interactions=total_interactions,
        total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        sessions=sliced_sessions,
        source_scope=source_scope.kind.value if source_scope else "local",
        sources_considered=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_succeeded=["local"]
        if source_scope is None or source_scope.kind == SourceScopeKind.LOCAL
        else [],
        sources_failed=[],
    )
