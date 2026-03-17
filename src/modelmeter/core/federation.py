"""Federation service for multi-source analytics."""

# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportUnusedImport=false

from __future__ import annotations

import base64
import json
import logging
import urllib.request
from datetime import date
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
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceFailure,
)


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
    )


# pyright: ignore[reportUnknownMemberType, reportUnknownArgumentType, reportAttributeAccessIssue]
def _merge_usage_data(usage_data: dict[str, int]) -> TokenUsage:
    """Create TokenUsage from usage data dict."""
    return TokenUsage(
        input_tokens=int(usage_data.get("input_tokens", 0)),
        output_tokens=int(usage_data.get("output_tokens", 0)),
        cache_read_tokens=int(usage_data.get("cache_read_tokens", 0)),
        cache_write_tokens=int(usage_data.get("cache_write_tokens", 0)),
    )


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

    query = "&".join(f"{k}={v}" for k, v in params.items())
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

    query = "&".join(f"{k}={v}" for k, v in params.items())
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

    query = "&".join(f"{k}={v}" for k, v in params.items())
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

    query = "&".join(f"{k}={v}" for k, v in params.items())
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

    query = "&".join(f"{k}={v}" for k, v in params.items())
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
) -> tuple[SummaryResponse, list[SourceFailure]]:
    """Execute a federated summary query across multiple sources."""
    from modelmeter.core.analytics import get_summary as get_local_summary
    from modelmeter.data.storage import resolve_storage_paths

    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None

    for source in sources:
        try:
            if source.kind == "sqlite":
                assert source.db_path is not None
                paths = resolve_storage_paths(settings, db_path_override=source.db_path)
                result = get_local_summary(
                    settings=settings,
                    days=days,
                    db_path_override=paths.sqlite_db_path,
                    token_source=token_source,  # type: ignore[arg-type]
                    session_count_source=session_count_source,  # type: ignore[arg-type]
                )
                total_usage = merge_token_usage(total_usage, result.usage)
                total_sessions += result.total_sessions
                if result.cost_usd is not None:
                    if total_cost is None:
                        total_cost = 0.0
                    total_cost += result.cost_usd
                if result.pricing_source:
                    pricing_source = result.pricing_source
            else:
                data = _fetch_http_summary(
                    source,
                    days=days,
                    token_source=token_source,
                    session_count_source=session_count_source,
                )
                usage_data_raw = data.get("usage")
                # pyright: ignore
                usage_data: dict[str, int] = (
                    usage_data_raw if isinstance(usage_data_raw, dict) else {}
                )  # type: ignore
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
        except Exception as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind="sqlite" if source.kind == "sqlite" else "http",
                )
            )

    return (
        SummaryResponse(
            usage=total_usage,
            total_sessions=total_sessions,
            window_days=days,
            cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            source_scope=scope_label,
            sources_considered=[s.source_id for s in sources],
            sources_succeeded=[
                s.source_id
                for s in sources
                if not any(f.source_id == s.source_id for f in failures)
            ],
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
) -> tuple[DailyResponse, list[SourceFailure]]:
    """Execute a federated daily query across multiple sources."""
    from modelmeter.core.analytics import get_daily as get_local_daily
    from modelmeter.data.storage import resolve_storage_paths

    daily_map: dict[date, DailyUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None

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
                    token_source=token_source,  # type: ignore[arg-type]
                    session_count_source=session_count_source,  # type: ignore[arg-type]
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
        except Exception as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind="sqlite" if source.kind == "sqlite" else "http",
                )
            )

    daily_rows = sorted(daily_map.values(), key=lambda x: x.day)

    return (
        DailyResponse(
            window_days=days,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            daily=daily_rows,
            source_scope=scope_label,
            sources_considered=[s.source_id for s in sources],
            sources_succeeded=[
                s.source_id
                for s in sources
                if not any(f.source_id == s.source_id for f in failures)
            ],
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
                while next_offset < total_remote_models:
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
        except Exception as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind="sqlite" if source.kind == "sqlite" else "http",
                )
            )

    total_models = len(model_map)
    priced_models = sum(1 for model in model_map.values() if model.has_pricing)
    unpriced_models = max(0, total_models - priced_models)
    models_rows = sorted(model_map.values(), key=lambda x: x.total_interactions, reverse=True)

    # Apply pagination after merge
    paginated_models = models_rows[offset : offset + limit]
    models_returned = len(paginated_models)

    return (
        ModelsResponse(
            window_days=days,
            models_offset=offset,
            models_limit=limit,
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
            sources_considered=[s.source_id for s in sources],
            sources_succeeded=[
                s.source_id
                for s in sources
                if not any(f.source_id == s.source_id for f in failures)
            ],
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
) -> tuple[ProvidersResponse, list[SourceFailure]]:
    """Execute a federated providers query across multiple sources."""
    from modelmeter.core.analytics import get_providers as get_local_providers
    from modelmeter.data.storage import resolve_storage_paths

    provider_map: dict[str, ProviderUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None

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
                while next_offset < total_remote_providers:
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
        except Exception as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind="sqlite" if source.kind == "sqlite" else "http",
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

    return (
        ProvidersResponse(
            window_days=days,
            providers_offset=offset,
            providers_limit=limit,
            providers_returned=providers_returned,
            total_providers=total_providers,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            providers=paginated_providers,
            source_scope=scope_label,
            sources_considered=[s.source_id for s in sources],
            sources_succeeded=[
                s.source_id
                for s in sources
                if not any(f.source_id == s.source_id for f in failures)
            ],
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
) -> tuple[ProjectsResponse, list[SourceFailure]]:
    """Execute a federated projects query across multiple sources."""
    from modelmeter.core.analytics import get_projects as get_local_projects
    from modelmeter.data.storage import resolve_storage_paths

    project_map: dict[str, ProjectUsage] = {}
    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None

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
                    if project.project_id in project_map:
                        project_map[project.project_id] = merge_project_usage(
                            project_map[project.project_id], project
                        )
                    else:
                        project_map[project.project_id] = project
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
                while next_offset < total_remote_projects:
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
                    )
                    if project_id in project_map:
                        project_map[project_id] = merge_project_usage(
                            project_map[project_id], project
                        )
                    else:
                        project_map[project_id] = project
        except Exception as e:
            failures.append(
                SourceFailure(
                    source_id=source.source_id,
                    error=str(e),
                    kind="sqlite" if source.kind == "sqlite" else "http",
                )
            )

    sorted_projects = sorted(project_map.values(), key=lambda x: x.usage.total_tokens, reverse=True)
    total_projects = len(sorted_projects)
    paginated_projects = (
        sorted_projects[offset : offset + limit] if limit > 0 else sorted_projects[offset:]
    )
    projects_returned = len(paginated_projects)

    return (
        ProjectsResponse(
            window_days=days,
            projects_offset=offset,
            projects_limit=limit,
            projects_returned=projects_returned,
            total_projects=total_projects,
            totals=total_usage,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            projects=paginated_projects,
            source_scope=scope_label,
            sources_considered=[s.source_id for s in sources],
            sources_succeeded=[
                s.source_id
                for s in sources
                if not any(f.source_id == s.source_id for f in failures)
            ],
            sources_failed=[{"source_id": f.source_id, "error": f.error} for f in failures],
        ),
        failures,
    )
