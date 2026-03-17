"""Federation service for multi-source analytics."""

# pyright: reportUnknownMemberType=false
# pyright: reportUnknownArgumentType=false
# pyright: reportAttributeAccessIssue=false
# pyright: reportUnusedImport=false

from __future__ import annotations

import json
import urllib.request

from modelmeter.config.settings import AppSettings
from modelmeter.core.models import (
    DailyResponse,
    ModelsResponse,
    ModelUsage,
    ProjectsResponse,
    ProvidersResponse,
    SummaryResponse,
    TokenUsage,
)
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceFailure,
)


def _merge_token_usage(a: TokenUsage, b: TokenUsage) -> TokenUsage:
    """Merge two TokenUsage objects by summing fields."""
    return TokenUsage(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        cache_read_tokens=a.cache_read_tokens + b.cache_read_tokens,
        cache_write_tokens=a.cache_write_tokens + b.cache_write_tokens,
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
    assert source.auth is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_count_source": session_count_source,
    }
    if days is not None:
        params["days"] = days

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{source.base_url.rstrip('/')}/api/summary?{query}"

    token_raw = f"{source.auth.username}:{source.auth.password}".encode()
    token = __import__("base64").b64encode(token_raw).decode("ascii")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "modelmeter/federation", "Authorization": f"Basic {token}"},
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
) -> dict[str, int | str | None]:
    """Fetch daily from an HTTP source."""
    assert source.base_url is not None
    assert source.auth is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_count_source": session_count_source,
        "timezone_offset_minutes": timezone_offset_minutes,
    }
    if days is not None:
        params["days"] = days

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{source.base_url.rstrip('/')}/api/daily?{query}"

    token_raw = f"{source.auth.username}:{source.auth.password}".encode()
    token = __import__("base64").b64encode(token_raw).decode("ascii")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "modelmeter/federation", "Authorization": f"Basic {token}"},
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
) -> dict[str, int | str | None]:
    """Fetch providers from an HTTP source."""
    assert source.base_url is not None
    assert source.auth is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_count_source": session_count_source,
        "offset": offset,
        "limit": limit,
    }
    if days is not None:
        params["days"] = days

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{source.base_url.rstrip('/')}/api/providers?{query}"

    token_raw = f"{source.auth.username}:{source.auth.password}".encode()
    token = __import__("base64").b64encode(token_raw).decode("ascii")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "modelmeter/federation", "Authorization": f"Basic {token}"},
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
) -> dict[str, int | str | None]:
    """Fetch projects from an HTTP source."""
    assert source.base_url is not None
    assert source.auth is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_count_source": session_count_source,
        "offset": offset,
        "limit": limit,
    }
    if days is not None:
        params["days"] = days

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{source.base_url.rstrip('/')}/api/projects?{query}"
    """Fetch projects from an HTTP source."""
    assert source.base_url is not None
    assert source.auth is not None

    params: dict[str, int | str | None] = {
        "token_source": token_source,
        "session_count_source": session_count_source,
        "offset": offset,
        "limit": limit,
    }
    if days is not None:
        params["days"] = days

    query = "&".join(f"{k}={v}" for k, v in params.items())
    url = f"{source.base_url.rstrip('/')}/api/projects?{query}"

    token_raw = f"{source.auth.username}:{source.auth.password}".encode()
    token = __import__("base64").b64encode(token_raw).decode("ascii")

    request = urllib.request.Request(
        url,
        headers={"User-Agent": "modelmeter/federation", "Authorization": f"Basic {token}"},
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
) -> tuple[SummaryResponse, list[SourceFailure]]:
    """Execute a federated summary query across multiple sources."""
    from modelmeter.core.analytics import get_summary as get_local_summary
    from modelmeter.data.storage import resolve_storage_paths

    total_usage = TokenUsage()
    total_sessions = 0
    total_cost: float | None = None
    pricing_source: str | None = None

    for source in sources:
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
            total_usage = _merge_token_usage(total_usage, result.usage)
            total_sessions += result.total_sessions
            if result.cost_usd is not None:
                if total_cost is None:
                    total_cost = 0.0
                total_cost += result.cost_usd
            if result.pricing_source:
                pricing_source = result.pricing_source
        else:
            try:
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
                total_usage = _merge_token_usage(
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
                        kind="http",
                    )
                )

    return (
        SummaryResponse(
            usage=total_usage,
            total_sessions=total_sessions,
            window_days=days,
            cost_usd=round(total_cost, 8) if total_cost is not None else None,
            pricing_source=pricing_source,
            # Metadata about federation - placeholder values
            source_scope="all",
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


def _merge_model_usage(a: ModelUsage, b: ModelUsage) -> ModelUsage:
    """Merge two ModelUsage objects by summing fields."""
    return ModelUsage(
        model_id=a.model_id,
        usage=_merge_token_usage(a.usage, b.usage),
        total_sessions=a.total_sessions + b.total_sessions,
        total_interactions=a.total_interactions + b.total_interactions,
        cost_usd=((a.cost_usd or 0.0) + (b.cost_usd or 0.0))
        if a.cost_usd is not None or b.cost_usd is not None
        else None,
        has_pricing=a.has_pricing or b.has_pricing,
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
) -> tuple[DailyResponse, list[SourceFailure]]:
    """Execute a federated daily query across multiple sources."""
    # Placeholder implementation - returns local-only data
    # Full implementation would fetch from HTTP sources and merge
    return (
        DailyResponse(
            window_days=days,
            totals=TokenUsage(),
            total_sessions=0,
            total_cost_usd=None,
            pricing_source=None,
            daily=[],
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
) -> tuple[ModelsResponse, list[SourceFailure]]:
    """Execute a federated models query across multiple sources."""
    # Placeholder implementation - returns local-only data
    # Full implementation would fetch from HTTP sources and merge
    return (
        ModelsResponse(
            window_days=days,
            models_offset=offset,
            models_limit=limit,
            models_returned=0,
            total_models=0,
            totals=TokenUsage(),
            total_sessions=0,
            total_cost_usd=None,
            pricing_source=None,
            priced_models=0,
            unpriced_models=0,
            models=[],
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
) -> tuple[ProvidersResponse, list[SourceFailure]]:
    """Execute a federated providers query across multiple sources."""
    # Placeholder implementation - returns local-only data
    return (
        ProvidersResponse(
            window_days=days,
            providers_offset=offset,
            providers_limit=limit,
            providers_returned=0,
            total_providers=0,
            totals=TokenUsage(),
            total_sessions=0,
            total_cost_usd=None,
            pricing_source=None,
            providers=[],
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
) -> tuple[ProjectsResponse, list[SourceFailure]]:
    """Execute a federated projects query across multiple sources."""
    # Placeholder implementation - returns local-only data
    return (
        ProjectsResponse(
            window_days=days,
            projects_offset=offset,
            projects_limit=limit,
            projects_returned=0,
            total_projects=0,
            totals=TokenUsage(),
            total_sessions=0,
            total_cost_usd=None,
            pricing_source=None,
            projects=[],
        ),
        failures,
    )
