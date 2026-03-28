"""Federation service for multi-source analytics."""

from __future__ import annotations

import base64
import json
import logging
import sqlite3
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any, cast

from modelmeter.config.settings import AppSettings
from modelmeter.core.models import (
    DailyResponse,
    DailyUsage,
    ModelsResponse,
    ModelUsage,
    ProjectsResponse,
    ProjectUsage,
    ProvidersResponse,
    ProviderUsage,
    SummaryResponse,
    TokenUsage,
)
from modelmeter.core.pricing import calculate_usage_cost, load_pricing_book
from modelmeter.core.providers import provider_from_model_id_and_provider_field
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceFailure,
)
from modelmeter.data.repository import create_repository

# Maximum number of items to fetch from a remote source to prevent memory exhaustion
MAX_FETCH_LIMIT = 5000


def _http_headers(source: DataSourceConfig) -> dict[str, str]:
    headers = {"User-Agent": "modelmeter/federation"}
    if source.auth is not None:
        token_raw = f"{source.auth.username}:{source.auth.password}".encode()
        token = base64.b64encode(token_raw).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    return headers


def merge_token_usage(a: TokenUsage, b: TokenUsage) -> TokenUsage:
    """Merge two TokenUsage objects by summing fields."""
    return TokenUsage(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        cache_read_tokens=a.cache_read_tokens + b.cache_read_tokens,
        cache_write_tokens=a.cache_write_tokens + b.cache_write_tokens,
    )


def merge_model_usage(a: ModelUsage, b: ModelUsage) -> ModelUsage:
    """Merge two ModelUsage objects by summing fields."""
    return ModelUsage(
        model_id=a.model_id,
        provider=a.provider or b.provider,
        usage=merge_token_usage(a.usage, b.usage),
        total_sessions=a.total_sessions + b.total_sessions,
        total_interactions=a.total_interactions + b.total_interactions,
        cost_usd=((a.cost_usd or 0.0) + (b.cost_usd or 0.0))
        if a.cost_usd is not None or b.cost_usd is not None
        else None,
        has_pricing=a.has_pricing or b.has_pricing,
    )


def merge_provider_usage(a: ProviderUsage, b: ProviderUsage) -> ProviderUsage:
    """Merge two ProviderUsage objects by summing fields."""
    return ProviderUsage(
        provider=a.provider,
        usage=merge_token_usage(a.usage, b.usage),
        total_models=a.total_models + b.total_models,
        total_interactions=a.total_interactions + b.total_interactions,
        cost_usd=((a.cost_usd or 0.0) + (b.cost_usd or 0.0))
        if a.cost_usd is not None or b.cost_usd is not None
        else None,
        has_pricing=a.has_pricing or b.has_pricing,
    )


def merge_project_usage(a: ProjectUsage, b: ProjectUsage) -> ProjectUsage:
    """Merge two ProjectUsage objects by summing fields."""
    return ProjectUsage(
        project_id=a.project_id,
        project_name=a.project_name,
        project_path=a.project_path or b.project_path,
        usage=merge_token_usage(a.usage, b.usage),
        total_sessions=a.total_sessions + b.total_sessions,
        total_interactions=a.total_interactions + b.total_interactions,
        cost_usd=((a.cost_usd or 0.0) + (b.cost_usd or 0.0))
        if a.cost_usd is not None or b.cost_usd is not None
        else None,
        has_pricing=a.has_pricing or b.has_pricing,
        sources=list(set(a.sources + b.sources)),
    )


def _merge_usage_data(usage_data: dict[str, int]) -> TokenUsage:
    """Create TokenUsage from usage data dict."""
    return TokenUsage(
        input_tokens=int(usage_data.get("input_tokens", 0)),
        output_tokens=int(usage_data.get("output_tokens", 0)),
        cache_read_tokens=int(usage_data.get("cache_read_tokens", usage_data.get("cache_read", 0))),
        cache_write_tokens=int(
            usage_data.get("cache_write_tokens", usage_data.get("cache_write", 0))
        ),
    )


def _canonical_model_id(model_id: str, provider_id: str | None = None) -> str:
    from modelmeter.core.analytics import _canonical_model_id as analytics_canonical_model_id

    return analytics_canonical_model_id(model_id, provider_id)


def _canonical_project_id(project_id: str, project_path: str | None) -> str:
    from modelmeter.core.analytics import _canonical_project_id as analytics_canonical_project_id

    return analytics_canonical_project_id(project_id, project_path)


def _fetch_http_summary(
    source: DataSourceConfig,
    *,
    days: int | None,
    token_source: str,
    session_count_source: str,
) -> dict[str, int | str | None]:
    """Fetch summary from an HTTP source."""
    assert source.base_url is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_source": session_count_source,
    }
    if days is not None:
        params["days"] = days

    query = urllib.parse.urlencode(params)
    url = f"{source.base_url.rstrip('/')}/api/summary?{query}"

    request = urllib.request.Request(
        url,
        headers=_http_headers(source),
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _fetch_http_daily(
    source: DataSourceConfig,
    *,
    days: int | None,
    timezone_offset_minutes: int,
    token_source: str,
    session_count_source: str,
) -> dict[str, object]:
    """Fetch daily usage from an HTTP source."""
    assert source.base_url is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_source": session_count_source,
        "timezone_offset_minutes": timezone_offset_minutes,
    }
    if days is not None:
        params["days"] = days

    query = urllib.parse.urlencode(params)
    url = f"{source.base_url.rstrip('/')}/api/daily?{query}"

    request = urllib.request.Request(
        url,
        headers=_http_headers(source),
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _fetch_http_models(
    source: DataSourceConfig,
    *,
    days: int | None,
    offset: int,
    limit: int,
    provider: str | None,
    token_source: str,
    session_count_source: str,
) -> dict[str, object]:
    """Fetch models from an HTTP source."""
    assert source.base_url is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_source": session_count_source,
        "offset": offset,
        "limit": limit,
    }
    if days is not None:
        params["days"] = days
    if provider is not None:
        params["provider"] = provider

    query = urllib.parse.urlencode(params)
    url = f"{source.base_url.rstrip('/')}/api/models?{query}"

    request = urllib.request.Request(
        url,
        headers=_http_headers(source),
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _fetch_http_providers(
    source: DataSourceConfig,
    *,
    days: int | None,
    offset: int,
    limit: int,
    token_source: str,
    session_count_source: str,
) -> dict[str, object]:
    """Fetch providers from an HTTP source."""
    assert source.base_url is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_source": session_count_source,
        "offset": offset,
        "limit": limit,
    }
    if days is not None:
        params["days"] = days

    query = urllib.parse.urlencode(params)
    url = f"{source.base_url.rstrip('/')}/api/providers?{query}"

    request = urllib.request.Request(
        url,
        headers=_http_headers(source),
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def _fetch_http_projects(
    source: DataSourceConfig,
    *,
    days: int | None,
    offset: int,
    limit: int,
    token_source: str,
    session_count_source: str,
) -> dict[str, object]:
    """Fetch projects from an HTTP source."""
    assert source.base_url is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_source": session_count_source,
        "offset": offset,
        "limit": limit,
    }
    if days is not None:
        params["days"] = days

    query = urllib.parse.urlencode(params)
    url = f"{source.base_url.rstrip('/')}/api/projects?{query}"

    request = urllib.request.Request(
        url,
        headers=_http_headers(source),
    )

    with urllib.request.urlopen(request, timeout=30) as response:
        return json.loads(response.read())


def execute_summary_federated(
    sources: list[DataSourceConfig],
    failures: list[SourceFailure],
    *,
    settings: AppSettings,
    days: int | None = None,
    token_source: str = "auto",
    session_count_source: str = "auto",
    scope_label: str = "all",
    pricing_file_override: Path | None = None,
) -> tuple[SummaryResponse, list[SourceFailure]]:
    """Execute a federated summary query across multiple sources."""
    from modelmeter.core.analytics import get_summary as get_local_summary
    from modelmeter.data.storage import resolve_storage_paths

    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None
    pricing_book, jsonl_pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    for source in sources:
        try:
            if source.kind == "sqlite":
                assert source.db_path is not None
                paths = resolve_storage_paths(settings, db_path_override=source.db_path)
                result = get_local_summary(
                    settings=settings,
                    days=days,
                    db_path_override=paths.sqlite_db_path,
                    token_source=token_source,  # ty: ignore[invalid-argument-type]
                    session_count_source=session_count_source,  # ty: ignore[invalid-argument-type]
                )
                total_usage = merge_token_usage(total_usage, result.usage)
                total_sessions += result.total_sessions
                if result.cost_usd is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += result.cost_usd
                if result.pricing_source:
                    pricing_source = result.pricing_source
            elif source.kind == "jsonl":
                assert source.db_path is not None
                repo = create_repository("jsonl", source.db_path)
                row = repo.fetch_summary(days=days)
                usage = _merge_usage_data(cast(dict[str, int], row))
                total_usage = merge_token_usage(total_usage, usage)
                total_sessions += repo.fetch_session_count(days=days)
                repo_cost = 0.0
                has_repo_cost = False
                for model_row in repo.fetch_model_usage(days=days):
                    model_id = _canonical_model_id(
                        str(model_row["model_id"]), cast(str | None, model_row.get("provider_id"))
                    )
                    pricing = pricing_book.get(model_id)
                    if pricing is None:
                        continue
                    repo_cost += calculate_usage_cost(
                        _merge_usage_data(cast(dict[str, int], model_row)), pricing
                    )
                    has_repo_cost = True
                if has_repo_cost:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += repo_cost
                    pricing_source = jsonl_pricing_source
            else:
                data = _fetch_http_summary(
                    source,
                    days=days,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                usage_data_raw = data.get("usage")
                usage_data: dict[str, int] = (
                    usage_data_raw if isinstance(usage_data_raw, dict) else {}
                )
                total_usage = merge_token_usage(
                    total_usage,
                    _merge_usage_data(usage_data),
                )
                total_sessions += int(data.get("total_sessions") or 0)
                cost_val = data.get("cost_usd")
                if cost_val is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += float(cost_val)
                pricing_val = data.get("pricing_source")
                if isinstance(pricing_val, str):
                    pricing_source = pricing_val
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            sqlite3.Error,
            json.JSONDecodeError,
            ValueError,
            KeyError,
            OSError,
        ) as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind=source.kind if source.kind in ("sqlite", "jsonl") else "http",
                )
            )

    _succeeded_ids = {
        s.source_id for s in sources if not any(f.source_id == s.source_id for f in failures)
    }
    _all_source_ids = list(
        dict.fromkeys([s.source_id for s in sources] + [f.source_id for f in failures])
    )
    return (
        SummaryResponse(
            usage=total_usage,
            total_sessions=total_sessions,
            window_days=days,
            cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            source_scope=scope_label,
            sources_considered=_all_source_ids,
            sources_succeeded=list(_succeeded_ids),
            sources_failed=[{"source_id": f.source_id, "error": f.error} for f in failures],
        ),
        failures,
    )


def execute_daily_federated(
    sources: list[DataSourceConfig],
    failures: list[SourceFailure],
    *,
    settings: AppSettings,
    days: int | None = None,
    timezone_offset_minutes: int = 0,
    token_source: str = "auto",
    session_count_source: str = "auto",
    scope_label: str = "all",
    pricing_file_override: Path | None = None,
) -> tuple[DailyResponse, list[SourceFailure]]:
    """Execute a federated daily query across multiple sources."""
    from modelmeter.core.analytics import get_daily as get_local_daily
    from modelmeter.data.storage import resolve_storage_paths

    daily_map: dict[date, DailyUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None
    pricing_book, jsonl_pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    for source in sources:
        try:
            if source.kind == "sqlite":
                assert source.db_path is not None
                paths = resolve_storage_paths(settings, db_path_override=source.db_path)
                result = get_local_daily(
                    settings=settings,
                    days=days,
                    timezone_offset_minutes=timezone_offset_minutes,
                    db_path_override=paths.sqlite_db_path,
                    token_source=token_source,  # ty: ignore[invalid-argument-type]
                    session_count_source=session_count_source,  # ty: ignore[invalid-argument-type]
                )
                total_usage = merge_token_usage(total_usage, result.totals)
                total_sessions += result.total_sessions
                if result.total_cost_usd is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += result.total_cost_usd
                if result.pricing_source:
                    pricing_source = result.pricing_source
                for daily_usage in result.daily:
                    if daily_usage.day in daily_map:
                        existing = daily_map[daily_usage.day]
                        daily_map[daily_usage.day] = DailyUsage(
                            day=daily_usage.day,
                            usage=merge_token_usage(existing.usage, daily_usage.usage),
                            total_sessions=existing.total_sessions + daily_usage.total_sessions,
                            cost_usd=((existing.cost_usd or 0.0) + (daily_usage.cost_usd or 0.0))
                            if existing.cost_usd is not None or daily_usage.cost_usd is not None
                            else None,
                        )
                    else:
                        daily_map[daily_usage.day] = daily_usage
            elif source.kind == "jsonl":
                assert source.db_path is not None
                repo = create_repository("jsonl", source.db_path)
                resolved_source = repo.resolve_token_source(
                    days=days,
                    token_source=token_source,  # ty: ignore[invalid-argument-type]
                )
                if resolved_source == "steps":
                    rows = repo.fetch_daily_steps(
                        days=days,
                        timezone_offset_minutes=timezone_offset_minutes,
                    )
                    summary_row = repo.fetch_summary_steps(days=days)
                else:
                    rows = repo.fetch_daily(
                        days=days, timezone_offset_minutes=timezone_offset_minutes
                    )
                    summary_row = repo.fetch_summary(days=days)
                repo_daily_costs: dict[date, float] = {}
                repo_total_cost = 0.0
                has_repo_cost = False
                for model_row in repo.fetch_daily_model_usage(
                    days=days,
                    timezone_offset_minutes=timezone_offset_minutes,
                ):
                    model_id = _canonical_model_id(
                        str(model_row["model_id"]), cast(str | None, model_row.get("provider_id"))
                    )
                    pricing = pricing_book.get(model_id)
                    if pricing is None:
                        continue
                    day_key = date.fromisoformat(str(model_row["day"]))
                    cost = calculate_usage_cost(
                        _merge_usage_data(cast(dict[str, int], model_row)), pricing
                    )
                    repo_daily_costs[day_key] = repo_daily_costs.get(day_key, 0.0) + cost
                    repo_total_cost += cost
                    has_repo_cost = True
                for row in rows:
                    day = date.fromisoformat(str(row["day"]))
                    usage = _merge_usage_data(cast(dict[str, int], row))
                    sessions = int(row.get("total_sessions", 0))
                    cost_usd = round(repo_daily_costs[day], 8) if day in repo_daily_costs else None
                    if day in daily_map:
                        existing = daily_map[day]
                        daily_map[day] = DailyUsage(
                            day=day,
                            usage=merge_token_usage(existing.usage, usage),
                            total_sessions=existing.total_sessions + sessions,
                            cost_usd=((existing.cost_usd or 0.0) + (cost_usd or 0.0))
                            if existing.cost_usd is not None or cost_usd is not None
                            else None,
                        )
                    else:
                        daily_map[day] = DailyUsage(
                            day=day, usage=usage, total_sessions=sessions, cost_usd=cost_usd
                        )
                total_usage = merge_token_usage(
                    total_usage,
                    _merge_usage_data(cast(dict[str, int], summary_row)),
                )
                if has_repo_cost:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += repo_total_cost
                    pricing_source = jsonl_pricing_source
                resolved_session_source = repo.resolve_session_count_source(
                    days=days,
                    session_count_source=session_count_source,  # ty: ignore[invalid-argument-type]
                )
                if resolved_session_source == "session":
                    total_sessions += repo.fetch_session_count(days=days)
                else:
                    total_sessions += int(summary_row.get("total_sessions", 0))
            else:
                data = _fetch_http_daily(
                    source,
                    days=days,
                    timezone_offset_minutes=timezone_offset_minutes,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                totals_data = cast("dict[str, Any]", data.get("totals", {}))
                total_usage = merge_token_usage(
                    total_usage,
                    TokenUsage(
                        input_tokens=int(cast(int, totals_data.get("input_tokens", 0))),
                        output_tokens=int(cast(int, totals_data.get("output_tokens", 0))),
                        cache_read_tokens=int(cast(int, totals_data.get("cache_read_tokens", 0))),
                        cache_write_tokens=int(cast(int, totals_data.get("cache_write_tokens", 0))),
                    ),
                )
                total_sessions += int(cast("int | None", data.get("total_sessions")) or 0)
                cost_val = cast("float | None", data.get("total_cost_usd"))
                if cost_val is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += float(cost_val)
                pricing_val = data.get("pricing_source")
                if isinstance(pricing_val, str):
                    pricing_source = pricing_val
                for daily_item in cast("list[dict[str, Any]]", data.get("daily", [])):
                    day = date.fromisoformat(str(daily_item["day"]))
                    daily_usage = DailyUsage(
                        day=day,
                        usage=TokenUsage(
                            input_tokens=daily_item.get("usage", {}).get("input_tokens", 0),
                            output_tokens=daily_item.get("usage", {}).get("output_tokens", 0),
                            cache_read_tokens=daily_item.get("usage", {}).get(
                                "cache_read_tokens", 0
                            ),
                            cache_write_tokens=daily_item.get("usage", {}).get(
                                "cache_write_tokens", 0
                            ),
                        ),
                        total_sessions=daily_item.get("total_sessions", 0),
                        cost_usd=daily_item.get("cost_usd"),
                    )
                    if day in daily_map:
                        existing = daily_map[day]
                        daily_map[day] = DailyUsage(
                            day=day,
                            usage=merge_token_usage(existing.usage, daily_usage.usage),
                            total_sessions=existing.total_sessions + daily_usage.total_sessions,
                            cost_usd=((existing.cost_usd or 0.0) + (daily_usage.cost_usd or 0.0))
                            if existing.cost_usd is not None or daily_usage.cost_usd is not None
                            else None,
                        )
                    else:
                        daily_map[day] = daily_usage
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            sqlite3.Error,
            json.JSONDecodeError,
            ValueError,
            KeyError,
            OSError,
        ) as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind=source.kind if source.kind in ("sqlite", "jsonl") else "http",
                )
            )

    daily_rows = sorted(daily_map.values(), key=lambda x: x.day)

    _succeeded_ids = {
        s.source_id for s in sources if not any(f.source_id == s.source_id for f in failures)
    }
    _all_source_ids = list(
        dict.fromkeys([s.source_id for s in sources] + [f.source_id for f in failures])
    )
    return (
        DailyResponse(
            window_days=days,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            daily=daily_rows,
            source_scope=scope_label,
            sources_considered=_all_source_ids,
            sources_succeeded=list(_succeeded_ids),
            sources_failed=[{"source_id": f.source_id, "error": f.error} for f in failures],
        ),
        failures,
    )


def execute_models_federated(
    sources: list[DataSourceConfig],
    failures: list[SourceFailure],
    *,
    settings: AppSettings,
    days: int | None = None,
    offset: int = 0,
    limit: int = 20,
    provider: str | None = None,
    token_source: str = "auto",
    session_count_source: str = "auto",
    scope_label: str = "all",
    pricing_file_override: Path | None = None,
) -> tuple[ModelsResponse, list[SourceFailure]]:
    """Execute a federated models query across multiple sources."""
    from modelmeter.core.analytics import get_models as get_local_models
    from modelmeter.data.storage import resolve_storage_paths

    model_map: dict[str, ModelUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_models = 0
    total_cost: float | None = None
    pricing_source: str | None = None
    priced_models = 0
    unpriced_models = 0
    pricing_book, jsonl_pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    for source in sources:
        try:
            if source.kind == "sqlite":
                assert source.db_path is not None
                paths = resolve_storage_paths(settings, db_path_override=source.db_path)
                result = get_local_models(
                    settings=settings,
                    days=days,
                    db_path_override=paths.sqlite_db_path,
                    provider=provider,
                    offset=0,
                    limit=0,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                typed_result: ModelsResponse = result
                total_usage = merge_token_usage(total_usage, typed_result.totals)
                total_sessions += typed_result.total_sessions
                if typed_result.total_cost_usd is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += typed_result.total_cost_usd
                if typed_result.pricing_source:
                    pricing_source = typed_result.pricing_source
                for model in typed_result.models:
                    if model.model_id in model_map:
                        model_map[model.model_id] = merge_model_usage(
                            model_map[model.model_id], model
                        )
                    else:
                        model_map[model.model_id] = model
            elif source.kind == "jsonl":
                assert source.db_path is not None
                repo = create_repository("jsonl", source.db_path)
                all_rows = repo.fetch_model_usage_detail(days=days)
                rows = [
                    row
                    for row in all_rows
                    if provider is None
                    or provider_from_model_id_and_provider_field(
                        str(row["model_id"]), cast(str | None, row.get("provider_id"))
                    )
                    == provider
                ]
                for row in rows:
                    model_id = _canonical_model_id(
                        str(row["model_id"]), cast(str | None, row.get("provider_id"))
                    )
                    usage = _merge_usage_data(cast(dict[str, int], row))
                    pricing = pricing_book.get(model_id)
                    cost_usd = (
                        round(calculate_usage_cost(usage, pricing), 8)
                        if pricing is not None
                        else None
                    )
                    model = ModelUsage(
                        model_id=model_id,
                        provider=provider_from_model_id_and_provider_field(
                            model_id, cast(str | None, row.get("provider_id"))
                        ),
                        usage=usage,
                        total_sessions=int(row.get("total_sessions", 0)),
                        total_interactions=int(row.get("total_interactions", 0)),
                        cost_usd=cost_usd,
                        has_pricing=pricing is not None,
                    )
                    if model_id in model_map:
                        model_map[model_id] = merge_model_usage(model_map[model_id], model)
                    else:
                        model_map[model_id] = model
                    if cost_usd is not None:
                        if total_cost is None:
                            total_cost = 0.0
                        total_cost += cost_usd
                        pricing_source = jsonl_pricing_source
                total_usage = merge_token_usage(
                    total_usage,
                    _merge_usage_data(cast(dict[str, int], repo.fetch_summary(days=days)))
                    if provider is None
                    else TokenUsage(
                        input_tokens=int(sum(int(r.get("input_tokens", 0)) for r in rows)),
                        output_tokens=int(sum(int(r.get("output_tokens", 0)) for r in rows)),
                        cache_read_tokens=int(
                            sum(
                                int(r.get("cache_read_tokens", r.get("cache_read", 0)))
                                for r in rows
                            )
                        ),
                        cache_write_tokens=int(
                            sum(
                                int(r.get("cache_write_tokens", r.get("cache_write", 0)))
                                for r in rows
                            )
                        ),
                    ),
                )
                total_sessions += (
                    repo.fetch_session_count(days=days)
                    if provider is None
                    else sum(int(r.get("total_sessions", 0)) for r in rows)
                )
            else:
                page_size = 1000
                data = _fetch_http_models(
                    source,
                    days=days,
                    offset=0,
                    limit=page_size,
                    provider=provider,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                totals_data = cast("dict[str, Any]", data.get("totals", {}))
                total_usage = merge_token_usage(
                    total_usage,
                    TokenUsage(
                        input_tokens=int(cast(int, totals_data.get("input_tokens", 0))),
                        output_tokens=int(cast(int, totals_data.get("output_tokens", 0))),
                        cache_read_tokens=int(cast(int, totals_data.get("cache_read_tokens", 0))),
                        cache_write_tokens=int(cast(int, totals_data.get("cache_write_tokens", 0))),
                    ),
                )
                total_sessions += int(cast("int | None", data.get("total_sessions")) or 0)
                cost_val = cast("float | None", data.get("total_cost_usd"))
                if cost_val is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += float(cost_val)
                pricing_val = data.get("pricing_source")
                if isinstance(pricing_val, str):
                    pricing_source = pricing_val

                models_list = list(cast("list[dict[str, Any]]", data.get("models", [])))
                total_remote_models = int(
                    cast("int | None", data.get("total_models")) or len(models_list)
                )
                next_offset = len(models_list)
                while next_offset < total_remote_models and len(models_list) < MAX_FETCH_LIMIT:
                    page_data = _fetch_http_models(
                        source,
                        days=days,
                        offset=next_offset,
                        limit=page_size,
                        provider=provider,
                        token_source=token_source,
                        session_count_source=session_count_source,
                    )
                    page_models = cast("list[dict[str, Any]]", page_data.get("models", []))
                    if not page_models:
                        break
                    models_list.extend(page_models)
                    next_offset += len(page_models)

                if len(models_list) >= MAX_FETCH_LIMIT:
                    logging.warning(
                        f"HTTP source {source.source_id} reached fetch limit "
                        f"({MAX_FETCH_LIMIT} items)"
                    )

                if models_list and "has_pricing" not in models_list[0]:
                    logging.warning(
                        f"HTTP source {source.source_id} response missing 'has_pricing' field - "
                        "API contract may have changed"
                    )
                for model_item in models_list:
                    model_id = str(model_item["model_id"])
                    model = ModelUsage(
                        model_id=model_id,
                        usage=TokenUsage(
                            input_tokens=model_item.get("usage", {}).get("input_tokens", 0),
                            output_tokens=model_item.get("usage", {}).get("output_tokens", 0),
                            cache_read_tokens=model_item.get("usage", {}).get(
                                "cache_read_tokens", 0
                            ),
                            cache_write_tokens=model_item.get("usage", {}).get(
                                "cache_write_tokens", 0
                            ),
                        ),
                        total_sessions=model_item.get("total_sessions", 0),
                        total_interactions=model_item.get("total_interactions", 0),
                        cost_usd=model_item.get("cost_usd"),
                        has_pricing=model_item.get("has_pricing", False),
                    )
                    if model_id in model_map:
                        model_map[model_id] = merge_model_usage(model_map[model_id], model)
                    else:
                        model_map[model_id] = model
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            sqlite3.Error,
            json.JSONDecodeError,
            ValueError,
            KeyError,
            OSError,
        ) as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind=source.kind if source.kind in ("sqlite", "jsonl") else "http",
                )
            )

    total_models = len(model_map)
    priced_models = sum(1 for model in model_map.values() if model.has_pricing)
    unpriced_models = max(0, total_models - priced_models)
    models_rows = sorted(model_map.values(), key=lambda x: x.total_interactions, reverse=True)

    # Apply pagination after merge (limit=0 means no limit)
    paginated_models = models_rows[offset : offset + limit] if limit > 0 else models_rows[offset:]
    models_returned = len(paginated_models)

    _succeeded_ids = {
        s.source_id for s in sources if not any(f.source_id == s.source_id for f in failures)
    }
    _all_source_ids = list(
        dict.fromkeys([s.source_id for s in sources] + [f.source_id for f in failures])
    )
    return (
        ModelsResponse(
            window_days=days,
            models_offset=offset,
            models_limit=limit if limit > 0 else None,
            models_returned=models_returned,
            total_models=total_models,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            priced_models=priced_models,
            unpriced_models=unpriced_models,
            models=paginated_models,
            source_scope=scope_label,
            sources_considered=_all_source_ids,
            sources_succeeded=list(_succeeded_ids),
            sources_failed=[{"source_id": f.source_id, "error": f.error} for f in failures],
        ),
        failures,
    )


def execute_providers_federated(
    sources: list[DataSourceConfig],
    failures: list[SourceFailure],
    *,
    settings: AppSettings,
    days: int | None = None,
    offset: int = 0,
    limit: int = 20,
    token_source: str = "auto",
    session_count_source: str = "auto",
    scope_label: str = "all",
    pricing_file_override: Path | None = None,
) -> tuple[ProvidersResponse, list[SourceFailure]]:
    """Execute a federated providers query across multiple sources."""
    from modelmeter.core.analytics import get_providers as get_local_providers
    from modelmeter.data.storage import resolve_storage_paths

    provider_map: dict[str, ProviderUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None
    pricing_book, jsonl_pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    for source in sources:
        try:
            if source.kind == "sqlite":
                assert source.db_path is not None
                paths = resolve_storage_paths(settings, db_path_override=source.db_path)
                result = get_local_providers(
                    settings=settings,
                    days=days,
                    db_path_override=paths.sqlite_db_path,
                    offset=0,
                    limit=0,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                typed_result: ProvidersResponse = result
                total_usage = merge_token_usage(total_usage, typed_result.totals)
                total_sessions += typed_result.total_sessions
                if typed_result.total_cost_usd is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += typed_result.total_cost_usd
                if typed_result.pricing_source:
                    pricing_source = typed_result.pricing_source
                for provider in typed_result.providers:
                    if provider.provider in provider_map:
                        provider_map[provider.provider] = merge_provider_usage(
                            provider_map[provider.provider], provider
                        )
                    else:
                        provider_map[provider.provider] = provider
            elif source.kind == "jsonl":
                assert source.db_path is not None
                repo = create_repository("jsonl", source.db_path)
                total_usage = merge_token_usage(
                    total_usage,
                    _merge_usage_data(cast(dict[str, int], repo.fetch_summary(days=days))),
                )
                rows = repo.fetch_model_usage_detail(days=days)
                provider_model_ids: dict[str, set[str]] = {}
                for row in rows:
                    model_id = _canonical_model_id(
                        str(row["model_id"]), cast(str | None, row.get("provider_id"))
                    )
                    provider = provider_from_model_id_and_provider_field(
                        model_id, cast(str | None, row.get("provider_id"))
                    )
                    if provider not in provider_model_ids:
                        provider_model_ids[provider] = set()
                    if model_id in provider_model_ids[provider]:
                        continue
                    provider_model_ids[provider].add(model_id)
                    usage = _merge_usage_data(cast(dict[str, int], row))
                    pricing = pricing_book.get(model_id)
                    cost_usd = (
                        round(calculate_usage_cost(usage, pricing), 8)
                        if pricing is not None
                        else None
                    )
                    if provider in provider_map:
                        existing = provider_map[provider]
                        provider_map[provider] = ProviderUsage(
                            provider=provider,
                            usage=merge_token_usage(existing.usage, usage),
                            total_models=len(provider_model_ids[provider]),
                            total_interactions=existing.total_interactions
                            + int(row.get("total_interactions", 0)),
                            cost_usd=((existing.cost_usd or 0.0) + (cost_usd or 0.0))
                            if existing.cost_usd is not None or cost_usd is not None
                            else None,
                            has_pricing=existing.has_pricing or pricing is not None,
                        )
                    else:
                        provider_map[provider] = ProviderUsage(
                            provider=provider,
                            usage=usage,
                            total_models=1,
                            total_interactions=int(row.get("total_interactions", 0)),
                            cost_usd=cost_usd,
                            has_pricing=pricing is not None,
                        )
                    if cost_usd is not None:
                        if total_cost is None:
                            total_cost = 0.0
                        total_cost += cost_usd
                        pricing_source = jsonl_pricing_source
                total_sessions += repo.fetch_session_count(days=days)
            else:
                page_size = 1000
                data = _fetch_http_providers(
                    source,
                    days=days,
                    offset=0,
                    limit=page_size,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                totals_data = cast("dict[str, Any]", data.get("totals", {}))
                total_usage = merge_token_usage(
                    total_usage,
                    TokenUsage(
                        input_tokens=int(cast(int, totals_data.get("input_tokens", 0))),
                        output_tokens=int(cast(int, totals_data.get("output_tokens", 0))),
                        cache_read_tokens=int(cast(int, totals_data.get("cache_read_tokens", 0))),
                        cache_write_tokens=int(cast(int, totals_data.get("cache_write_tokens", 0))),
                    ),
                )
                total_sessions += int(cast("int | None", data.get("total_sessions")) or 0)
                cost_val = cast("float | None", data.get("total_cost_usd"))
                if cost_val is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += float(cost_val)
                pricing_val = data.get("pricing_source")
                if isinstance(pricing_val, str):
                    pricing_source = pricing_val

                provider_items = list(cast("list[dict[str, Any]]", data.get("providers", [])))
                total_remote_providers = int(
                    cast("int | None", data.get("total_providers")) or len(provider_items)
                )
                next_offset = len(provider_items)
                while (
                    next_offset < total_remote_providers and len(provider_items) < MAX_FETCH_LIMIT
                ):
                    page_data = _fetch_http_providers(
                        source,
                        days=days,
                        offset=next_offset,
                        limit=page_size,
                        token_source=token_source,
                        session_count_source=session_count_source,
                    )
                    page_providers = cast("list[dict[str, Any]]", page_data.get("providers", []))
                    if not page_providers:
                        break
                    provider_items.extend(page_providers)
                    next_offset += len(page_providers)

                if len(provider_items) >= MAX_FETCH_LIMIT:
                    logging.warning(
                        f"HTTP source {source.source_id} reached fetch limit "
                        f"({MAX_FETCH_LIMIT} items)"
                    )

                for provider_item in provider_items:
                    provider_name = str(provider_item["provider"])
                    usage_dict = cast("dict[str, Any]", provider_item.get("usage", {}))
                    provider = ProviderUsage(
                        provider=provider_name,
                        usage=TokenUsage(
                            input_tokens=usage_dict.get("input_tokens", 0),
                            output_tokens=usage_dict.get("output_tokens", 0),
                            cache_read_tokens=usage_dict.get("cache_read_tokens", 0),
                            cache_write_tokens=usage_dict.get("cache_write_tokens", 0),
                        ),
                        total_models=provider_item.get("total_models", 0),
                        total_interactions=provider_item.get("total_interactions", 0),
                        cost_usd=provider_item.get("cost_usd"),
                        has_pricing=provider_item.get("has_pricing", False),
                    )
                    if provider_name in provider_map:
                        provider_map[provider_name] = merge_provider_usage(
                            provider_map[provider_name], provider
                        )
                    else:
                        provider_map[provider_name] = provider
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            sqlite3.Error,
            json.JSONDecodeError,
            ValueError,
            KeyError,
            OSError,
        ) as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind=source.kind if source.kind in ("sqlite", "jsonl") else "http",
                )
            )

    sorted_providers = sorted(
        provider_map.values(), key=lambda x: x.usage.total_tokens, reverse=True
    )
    total_providers = len(sorted_providers)
    paginated_providers = (
        sorted_providers[offset : offset + limit] if limit > 0 else sorted_providers[offset:]
    )
    providers_returned = len(paginated_providers)

    _succeeded_ids = {
        s.source_id for s in sources if not any(f.source_id == s.source_id for f in failures)
    }
    _all_source_ids = list(
        dict.fromkeys([s.source_id for s in sources] + [f.source_id for f in failures])
    )
    return (
        ProvidersResponse(
            window_days=days,
            providers_offset=offset,
            providers_limit=limit if limit > 0 else None,
            providers_returned=providers_returned,
            total_providers=total_providers,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            providers=paginated_providers,
            source_scope=scope_label,
            sources_considered=_all_source_ids,
            sources_succeeded=list(_succeeded_ids),
            sources_failed=[{"source_id": f.source_id, "error": f.error} for f in failures],
        ),
        failures,
    )


def execute_projects_federated(
    sources: list[DataSourceConfig],
    failures: list[SourceFailure],
    *,
    settings: AppSettings,
    days: int | None = None,
    offset: int = 0,
    limit: int = 20,
    token_source: str = "auto",
    session_count_source: str = "auto",
    scope_label: str = "all",
    pricing_file_override: Path | None = None,
) -> tuple[ProjectsResponse, list[SourceFailure]]:
    """Execute a federated projects query across multiple sources."""
    from modelmeter.core.analytics import get_projects as get_local_projects
    from modelmeter.data.storage import resolve_storage_paths

    project_map: dict[str, ProjectUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None
    pricing_book, jsonl_pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    for source in sources:
        try:
            if source.kind == "sqlite":
                assert source.db_path is not None
                paths = resolve_storage_paths(settings, db_path_override=source.db_path)
                result = get_local_projects(
                    settings=settings,
                    days=days,
                    db_path_override=paths.sqlite_db_path,
                    offset=0,
                    limit=0,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                typed_result: ProjectsResponse = result
                total_usage = merge_token_usage(total_usage, typed_result.totals)
                total_sessions += typed_result.total_sessions
                if typed_result.total_cost_usd is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += typed_result.total_cost_usd
                if typed_result.pricing_source:
                    pricing_source = typed_result.pricing_source
                for project in typed_result.projects:
                    project_with_source = ProjectUsage(
                        project_id=project.project_id,
                        project_name=project.project_name,
                        project_path=project.project_path,
                        usage=project.usage,
                        total_sessions=project.total_sessions,
                        total_interactions=project.total_interactions,
                        cost_usd=project.cost_usd,
                        has_pricing=project.has_pricing,
                        sources=[source.source_id],
                    )
                    if project.project_id in project_map:
                        project_map[project.project_id] = merge_project_usage(
                            project_map[project.project_id], project_with_source
                        )
                    else:
                        project_map[project.project_id] = project_with_source
            elif source.kind == "jsonl":
                assert source.db_path is not None
                repo = create_repository("jsonl", source.db_path)
                total_usage = merge_token_usage(
                    total_usage,
                    _merge_usage_data(cast(dict[str, int], repo.fetch_summary(days=days))),
                )
                rows = repo.fetch_project_usage_detail(days=days)
                project_paths = {
                    str(row["project_id"]): cast(str | None, row.get("project_path"))
                    for row in rows
                }
                project_cost_map: dict[str, float] = {}
                for row in repo.fetch_project_model_usage(days=days):
                    project_path = project_paths.get(str(row["project_id"]))
                    project_id = _canonical_project_id(str(row["project_id"]), project_path)
                    model_id = _canonical_model_id(
                        str(row["model_id"]), cast(str | None, row.get("provider_id"))
                    )
                    pricing = pricing_book.get(model_id)
                    if pricing is None:
                        continue
                    cost = calculate_usage_cost(
                        _merge_usage_data(cast(dict[str, int], row)), pricing
                    )
                    project_cost_map[project_id] = project_cost_map.get(project_id, 0.0) + cost
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += cost
                    pricing_source = jsonl_pricing_source
                for row in rows:
                    project_id = _canonical_project_id(
                        str(row["project_id"]), cast(str | None, row.get("project_path"))
                    )
                    usage = _merge_usage_data(cast(dict[str, int], row))
                    project_with_source = ProjectUsage(
                        project_id=project_id,
                        project_name=str(row.get("project_name", project_id)),
                        project_path=cast(str | None, row.get("project_path")),
                        usage=usage,
                        total_sessions=int(row.get("total_sessions", 0)),
                        total_interactions=int(row.get("total_interactions", 0)),
                        cost_usd=round(project_cost_map[project_id], 8)
                        if project_id in project_cost_map
                        else None,
                        has_pricing=project_id in project_cost_map,
                        sources=[source.source_id],
                    )
                    if project_id in project_map:
                        project_map[project_id] = merge_project_usage(
                            project_map[project_id], project_with_source
                        )
                    else:
                        project_map[project_id] = project_with_source
                total_sessions += repo.fetch_session_count(days=days)
            else:
                page_size = 1000
                data = _fetch_http_projects(
                    source,
                    days=days,
                    offset=0,
                    limit=page_size,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                totals_data = cast("dict[str, Any]", data.get("totals", {}))
                total_usage = merge_token_usage(
                    total_usage,
                    TokenUsage(
                        input_tokens=int(cast(int, totals_data.get("input_tokens", 0))),
                        output_tokens=int(cast(int, totals_data.get("output_tokens", 0))),
                        cache_read_tokens=int(cast(int, totals_data.get("cache_read_tokens", 0))),
                        cache_write_tokens=int(cast(int, totals_data.get("cache_write_tokens", 0))),
                    ),
                )
                total_sessions += int(cast("int | None", data.get("total_sessions")) or 0)
                cost_val = cast("float | None", data.get("total_cost_usd"))
                if cost_val is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += float(cost_val)
                pricing_val = data.get("pricing_source")
                if isinstance(pricing_val, str):
                    pricing_source = pricing_val

                project_items = list(cast("list[dict[str, Any]]", data.get("projects", [])))
                total_remote_projects = int(
                    cast("int | None", data.get("total_projects")) or len(project_items)
                )
                next_offset = len(project_items)
                while next_offset < total_remote_projects and len(project_items) < MAX_FETCH_LIMIT:
                    page_data = _fetch_http_projects(
                        source,
                        days=days,
                        offset=next_offset,
                        limit=page_size,
                        token_source=token_source,
                        session_count_source=session_count_source,
                    )
                    page_projects = cast("list[dict[str, Any]]", page_data.get("projects", []))
                    if not page_projects:
                        break
                    project_items.extend(page_projects)
                    next_offset += len(page_projects)

                if len(project_items) >= MAX_FETCH_LIMIT:
                    logging.warning(
                        f"HTTP source {source.source_id} reached fetch limit "
                        f"({MAX_FETCH_LIMIT} items)"
                    )

                for project_item in project_items:
                    project_id = str(project_item["project_id"])
                    usage_dict = cast("dict[str, Any]", project_item.get("usage", {}))
                    project = ProjectUsage(
                        project_id=project_id,
                        project_name=str(project_item["project_name"]),
                        project_path=project_item.get("project_path"),
                        usage=TokenUsage(
                            input_tokens=usage_dict.get("input_tokens", 0),
                            output_tokens=usage_dict.get("output_tokens", 0),
                            cache_read_tokens=usage_dict.get("cache_read_tokens", 0),
                            cache_write_tokens=usage_dict.get("cache_write_tokens", 0),
                        ),
                        total_sessions=project_item.get("total_sessions", 0),
                        total_interactions=project_item.get("total_interactions", 0),
                        cost_usd=project_item.get("cost_usd"),
                        has_pricing=project_item.get("has_pricing", False),
                        sources=[source.source_id],
                    )
                    if project_id in project_map:
                        project_map[project_id] = merge_project_usage(
                            project_map[project_id], project
                        )
                    else:
                        project_map[project_id] = project
        except (
            urllib.error.URLError,
            urllib.error.HTTPError,
            sqlite3.Error,
            json.JSONDecodeError,
            ValueError,
            KeyError,
            OSError,
        ) as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind=source.kind if source.kind in ("sqlite", "jsonl") else "http",
                )
            )

    sorted_projects = sorted(project_map.values(), key=lambda x: x.usage.total_tokens, reverse=True)
    total_projects = len(sorted_projects)
    paginated_projects = (
        sorted_projects[offset : offset + limit] if limit > 0 else sorted_projects[offset:]
    )
    projects_returned = len(paginated_projects)

    _succeeded_ids = {
        s.source_id for s in sources if not any(f.source_id == s.source_id for f in failures)
    }
    _all_source_ids = list(
        dict.fromkeys([s.source_id for s in sources] + [f.source_id for f in failures])
    )
    return (
        ProjectsResponse(
            window_days=days,
            projects_offset=offset,
            projects_limit=limit if limit > 0 else None,
            projects_returned=projects_returned,
            total_projects=total_projects,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            projects=paginated_projects,
            source_scope=scope_label,
            sources_considered=_all_source_ids,
            sources_succeeded=list(_succeeded_ids),
            sources_failed=[{"source_id": f.source_id, "error": f.error} for f in failures],
        ),
        failures,
    )
