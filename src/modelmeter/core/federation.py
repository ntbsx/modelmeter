"""Federation service for multi-source analytics."""

from __future__ import annotations

import json
import urllib.request

from modelmeter.config.settings import AppSettings
from modelmeter.core.models import (
    SummaryResponse,
    TokenUsage,
)
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceFailure,
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


def _merge_token_usage(a: TokenUsage, b: TokenUsage) -> TokenUsage:
    """Merge two TokenUsage objects by summing fields."""
    return TokenUsage(
        input_tokens=a.input_tokens + b.input_tokens,
        output_tokens=a.output_tokens + b.output_tokens,
        cache_read_tokens=a.cache_read_tokens + b.cache_read_tokens,
        cache_write_tokens=a.cache_write_tokens + b.cache_write_tokens,
    )


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
                usage_data: dict[str, int] = data.get("usage", {})  # type: ignore[assignment]
                total_usage = _merge_token_usage(
                    total_usage,
                    TokenUsage(
                        input_tokens=usage_data.get("input_tokens", 0),
                        output_tokens=usage_data.get("output_tokens", 0),
                        cache_read_tokens=usage_data.get("cache_read_tokens", 0),
                        cache_write_tokens=usage_data.get("cache_write_tokens", 0),
                    ),
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
        ),
        failures,
    )
