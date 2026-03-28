"""Analytics services for summary and daily usage."""

from __future__ import annotations

import sqlite3
from datetime import UTC, date, datetime
from hashlib import md5
from pathlib import Path
from typing import Any, Literal

from modelmeter.config.settings import AppSettings
from modelmeter.core.doctor import generate_doctor_report
from modelmeter.core.federation import merge_project_usage
from modelmeter.core.models import (
    DailyResponse,
    DailyUsage,
    DateInsightsResponse,
    ModelDetailResponse,
    ModelsResponse,
    ModelUsage,
    ProjectDetailResponse,
    ProjectModelUsage,
    ProjectSessionUsage,
    ProjectsResponse,
    ProjectUsage,
    ProvidersResponse,
    ProviderUsage,
    SessionModelUsage,
    SessionUsage,
    SummaryResponse,
    TokenUsage,
)
from modelmeter.core.pricing import calculate_usage_cost, load_pricing_book
from modelmeter.core.providers import provider_from_model_id_and_provider_field
from modelmeter.core.sources import SourceScope, SourceScopeKind
from modelmeter.data.repository import UsageRepository, create_repository
from modelmeter.data.storage import resolve_storage_paths


def _token_usage_from_row(row: dict[str, Any]) -> TokenUsage:
    mapping = row
    return TokenUsage(
        input_tokens=int(mapping.get("input_tokens", 0)),
        output_tokens=int(mapping.get("output_tokens", 0)),
        cache_read_tokens=int(mapping.get("cache_read_tokens", mapping.get("cache_read", 0))),
        cache_write_tokens=int(mapping.get("cache_write_tokens", mapping.get("cache_write", 0))),
    )


def _resolved_summary_row(
    repository: UsageRepository,
    *,
    days: int | None,
    token_source: Literal["auto", "message", "steps"],
) -> dict[str, Any]:
    resolved_token_source = repository.resolve_token_source(
        days=days,
        token_source=token_source,
    )
    if resolved_token_source == "steps":
        return repository.fetch_summary_steps(days=days)
    return repository.fetch_summary(days=days)


def _resolved_total_sessions(
    repository: UsageRepository,
    *,
    days: int | None,
    session_count_source: Literal["auto", "activity", "session"],
    summary_row: dict[str, Any],
) -> int:
    resolved_session_source = repository.resolve_session_count_source(
        days=days,
        session_count_source=session_count_source,
    )
    if resolved_session_source == "activity":
        return int(summary_row["total_sessions"])
    return repository.fetch_session_count(days=days)


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


def _canonical_model_id(model_id: str, provider_id: str | None = None) -> str:
    if "/" in model_id:
        return model_id
    provider = provider_from_model_id_and_provider_field(model_id, provider_id)
    if provider and provider != "unknown":
        return f"{provider}/{model_id}"
    return model_id


def _canonical_project_id(project_id: str, project_path: str | None) -> str:
    if not project_path:
        return project_id
    return f"local:{md5(project_path.encode()).hexdigest()[:16]}"


def _pricing_for_row(pricing_book: dict[str, Any], row: dict[str, Any]) -> Any:
    model_id = _canonical_model_id(str(row["model_id"]), row.get("provider_id"))
    return pricing_book.get(model_id)


def _resolve_local_repositories(
    settings: AppSettings,
    db_path_override: Path | None = None,
) -> list[tuple[str, UsageRepository]]:
    """Resolve all available local data repositories."""
    repos: list[tuple[str, UsageRepository]] = []

    try:
        sqlite_path = _resolve_sqlite_path(settings, db_path_override)
        repos.append(("local-opencode", create_repository("sqlite", sqlite_path)))
    except RuntimeError:
        pass

    if db_path_override is None and settings.claudecode_enabled:
        projects_dir = settings.claudecode_data_dir / "projects"
        if projects_dir.exists() and any(projects_dir.rglob("*.jsonl")):
            repos.append(
                ("local-claudecode", create_repository("jsonl", settings.claudecode_data_dir))
            )

    return repos


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
        canonical_model_id = _canonical_model_id(row.model_id, row.provider)
        normalized_row = row.model_copy(update={"model_id": canonical_model_id})
        existing = merged.get(canonical_model_id)
        if existing is None:
            merged[canonical_model_id] = normalized_row
        else:
            merged[canonical_model_id] = merge_model_usage(existing, normalized_row)
    return sorted(merged.values(), key=lambda item: item.usage.total_tokens, reverse=True)


def _merge_provider_rows(
    local_rows: list[ProviderUsage], federated_rows: list[ProviderUsage]
) -> list[ProviderUsage]:
    from modelmeter.core.federation import merge_provider_usage

    result: dict[str, ProviderUsage] = {}
    for row in local_rows:
        if row.provider in result:
            result[row.provider] = merge_provider_usage(result[row.provider], row)
        else:
            result[row.provider] = row
    for row in federated_rows:
        if row.provider in result:
            result[row.provider] = merge_provider_usage(result[row.provider], row)
        else:
            result[row.provider] = row
    return list(result.values())


def _merge_project_rows(
    local_rows: list[ProjectUsage], federated_rows: list[ProjectUsage]
) -> list[ProjectUsage]:
    merged: dict[str, ProjectUsage] = {}
    for row in local_rows + federated_rows:
        canonical_project_id = _canonical_project_id(row.project_id, row.project_path)
        normalized_row = row.model_copy(update={"project_id": canonical_project_id})
        merge_key = row.project_path or canonical_project_id
        existing = merged.get(merge_key)
        if existing is None:
            merged[merge_key] = normalized_row
        else:
            merged[merge_key] = merge_project_usage(existing, normalized_row)
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
            pricing_file_override=pricing_file_override,
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
            pricing_file_override=pricing_file_override,
        )
        return result

    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    if len(local_repos) == 1:
        _, repository = local_repos[0]

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

        cost_usd: float | None = None
        if pricing_book:
            total_cost = 0.0
            for model_row in model_rows:
                pricing = _pricing_for_row(pricing_book, model_row)
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
            sources_considered=[local_repos[0][0]],
            sources_succeeded=[local_repos[0][0]],
            sources_failed=[],
        )

    merged_usage = TokenUsage()
    merged_sessions = 0
    merged_cost = 0.0
    has_cost = False
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
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
                total_sessions = repository.fetch_session_count(days=days)
            elif session_count_source == "session":
                total_sessions = repository.fetch_session_count(days=days)
            else:
                total_sessions = int(row["total_sessions"])

            merged_usage = merge_token_usage(merged_usage, _token_usage_from_row(row))
            merged_sessions += total_sessions

            if pricing_book:
                repo_cost = 0.0
                for model_row in repository.fetch_model_usage(days=days):
                    pricing = _pricing_for_row(pricing_book, model_row)
                    if pricing is None:
                        continue
                    repo_cost += calculate_usage_cost(_token_usage_from_row(model_row), pricing)
                merged_cost += repo_cost
                has_cost = True

            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    return SummaryResponse(
        usage=merged_usage,
        total_sessions=merged_sessions,
        window_days=days,
        cost_usd=round(merged_cost, 8) if has_cost else None,
        pricing_source=pricing_source,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
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
            pricing_file_override=pricing_file_override,
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
            pricing_file_override=pricing_file_override,
        )
        return result
    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    if len(local_repos) == 1:
        _, repository = local_repos[0]
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
            rows = repository.fetch_daily(
                days=days, timezone_offset_minutes=timezone_offset_minutes
            )
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

        daily_cost_map: dict[str, float] = {}
        total_cost_usd: float | None = None
        if pricing_book:
            total_cost_usd = 0.0
            for model_row in daily_model_rows:
                pricing = _pricing_for_row(pricing_book, model_row)
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
            sources_considered=[local_repos[0][0]],
            sources_succeeded=[local_repos[0][0]],
            sources_failed=[],
        )

    merged_totals = TokenUsage()
    merged_total_sessions = 0
    merged_daily_rows: list[DailyUsage] = []
    merged_total_cost = 0.0
    has_cost = False
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
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
                rows = repository.fetch_daily(
                    days=days, timezone_offset_minutes=timezone_offset_minutes
                )
                summary_row = repository.fetch_summary(days=days)

            daily_session_counts = repository.fetch_daily_session_counts(
                days=days,
                timezone_offset_minutes=timezone_offset_minutes,
            )
            if resolved_session_source == "session":
                total_sessions = repository.fetch_session_count(days=days)
            else:
                total_sessions = int(summary_row["total_sessions"])

            merged_totals = merge_token_usage(merged_totals, _token_usage_from_row(summary_row))
            merged_total_sessions += total_sessions

            repo_daily_rows: list[DailyUsage] = []
            for row in rows:
                parsed_day = date.fromisoformat(str(row["day"]))
                if resolved_session_source == "session":
                    sessions = daily_session_counts.get(parsed_day.isoformat(), 0)
                else:
                    sessions = int(row["total_sessions"])
                repo_daily_rows.append(
                    DailyUsage(
                        day=parsed_day,
                        usage=_token_usage_from_row(row),
                        total_sessions=sessions,
                        cost_usd=None,
                    )
                )
            merged_daily_rows = _merge_daily_rows(merged_daily_rows, repo_daily_rows)

            if pricing_book:
                repo_total_cost = 0.0
                repo_daily_cost_map: dict[str, float] = {}
                for model_row in repository.fetch_daily_model_usage(
                    days=days,
                    timezone_offset_minutes=timezone_offset_minutes,
                ):
                    pricing = _pricing_for_row(pricing_book, model_row)
                    if pricing is None:
                        continue
                    day_key = str(model_row["day"])
                    cost = calculate_usage_cost(_token_usage_from_row(model_row), pricing)
                    repo_daily_cost_map[day_key] = repo_daily_cost_map.get(day_key, 0.0) + cost
                    repo_total_cost += cost
                if repo_daily_cost_map:
                    merged_daily_rows = _merge_daily_rows(
                        merged_daily_rows,
                        [
                            DailyUsage(
                                day=date.fromisoformat(day_key),
                                usage=TokenUsage(),
                                total_sessions=0,
                                cost_usd=round(cost, 8),
                            )
                            for day_key, cost in repo_daily_cost_map.items()
                        ],
                    )
                merged_total_cost += repo_total_cost
                has_cost = True

            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    return DailyResponse(
        window_days=days,
        totals=merged_totals,
        total_sessions=merged_total_sessions,
        total_cost_usd=round(merged_total_cost, 8) if has_cost else None,
        pricing_source=pricing_source,
        daily=merged_daily_rows,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
    )


def get_date_insights(
    *,
    settings: AppSettings,
    day: date,
    timezone_offset_minutes: int = 0,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    token_source: Literal["auto", "message", "steps"] = "auto",
    source_scope: SourceScope | None = None,
) -> DateInsightsResponse:
    """Return date-specific totals and breakdowns."""
    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        raise NotImplementedError("Federated date insights are not yet implemented")

    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    day_str = day.isoformat()

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    def _build_date_insights(
        repo: UsageRepository, source_id: str
    ) -> tuple[
        dict[str, Any],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        list[dict[str, Any]],
        bool,
        int,
    ]:
        use_steps = False
        if token_source == "auto":
            steps_row = repo.fetch_summary_for_day_steps(
                day=day_str,
                timezone_offset_minutes=timezone_offset_minutes,
            )
            if steps_row is not None and int(steps_row["total_sessions"]) > 0:
                summary_row = steps_row
                use_steps = True
            else:
                summary_row = repo.fetch_summary_for_day(
                    day=day_str,
                    timezone_offset_minutes=timezone_offset_minutes,
                )
        elif token_source == "steps":
            summary_row = repo.fetch_summary_for_day_steps(
                day=day_str,
                timezone_offset_minutes=timezone_offset_minutes,
            )
            use_steps = True
        else:
            summary_row = repo.fetch_summary_for_day(
                day=day_str,
                timezone_offset_minutes=timezone_offset_minutes,
            )

        if summary_row is None:
            raise RuntimeError("Date summary query returned no row")

        model_rows = repo.fetch_model_usage_detail_for_day(
            day=day_str,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        project_rows = repo.fetch_project_usage_detail_for_day(
            day=day_str,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        project_model_rows = repo.fetch_project_model_usage_for_day(
            day=day_str,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        session_model_rows = repo.fetch_session_model_usage_for_day(
            day=day_str,
            timezone_offset_minutes=timezone_offset_minutes,
        )

        interactions_from_models = sum(int(r["total_interactions"]) for r in model_rows)
        total_interactions = (
            interactions_from_models if use_steps else int(summary_row["total_interactions"])
        )

        return (
            summary_row,
            model_rows,
            project_rows,
            project_model_rows,
            session_model_rows,
            use_steps,
            total_interactions,
        )

    def _build_models_from_rows(
        model_rows: list[dict[str, Any]],
    ) -> tuple[list[ModelUsage], dict[str, ProviderUsage], float | None, int]:
        models: list[ModelUsage] = []
        provider_map: dict[str, ProviderUsage] = {}
        total_cost_usd: float | None = 0.0 if pricing_book else None
        interactions_from_models = 0

        for row in model_rows:
            mid = _canonical_model_id(str(row["model_id"]), row["provider_id"])
            usage = _token_usage_from_row(row)
            pricing = pricing_book.get(mid)
            cost_usd: float | None = None
            if pricing is not None:
                cost_usd = round(calculate_usage_cost(usage, pricing), 8)
                if total_cost_usd is not None:
                    total_cost_usd += cost_usd

            provider = provider_from_model_id_and_provider_field(mid, row["provider_id"])
            model = ModelUsage(
                model_id=mid,
                provider=provider,
                usage=usage,
                total_sessions=int(row["total_sessions"]),
                total_interactions=int(row["total_interactions"]),
                cost_usd=cost_usd,
                has_pricing=pricing is not None,
            )
            existing_model = next((m for m in models if m.model_id == mid), None)
            if existing_model is None:
                models.append(model)
            else:
                existing_model.usage.input_tokens += usage.input_tokens
                existing_model.usage.output_tokens += usage.output_tokens
                existing_model.usage.cache_read_tokens += usage.cache_read_tokens
                existing_model.usage.cache_write_tokens += usage.cache_write_tokens
                existing_model.total_sessions += int(row["total_sessions"])
                existing_model.total_interactions += int(row["total_interactions"])
                if cost_usd is not None:
                    existing_model.has_pricing = True
                    if existing_model.cost_usd is None:
                        existing_model.cost_usd = cost_usd
                    else:
                        existing_model.cost_usd = round(existing_model.cost_usd + cost_usd, 8)
            interactions_from_models += int(row["total_interactions"])
            existing_provider = provider_map.get(provider)
            if existing_provider is None:
                provider_map[provider] = ProviderUsage(
                    provider=provider,
                    usage=TokenUsage(
                        input_tokens=usage.input_tokens,
                        output_tokens=usage.output_tokens,
                        cache_read_tokens=usage.cache_read_tokens,
                        cache_write_tokens=usage.cache_write_tokens,
                    ),
                    total_models=1,
                    total_interactions=model.total_interactions,
                    cost_usd=cost_usd,
                    has_pricing=cost_usd is not None,
                )
            else:
                existing_provider.usage.input_tokens += usage.input_tokens
                existing_provider.usage.output_tokens += usage.output_tokens
                existing_provider.usage.cache_read_tokens += usage.cache_read_tokens
                existing_provider.usage.cache_write_tokens += usage.cache_write_tokens
                existing_provider.total_models += 1
                existing_provider.total_interactions += model.total_interactions
                if cost_usd is not None:
                    existing_provider.has_pricing = True
                    if existing_provider.cost_usd is None:
                        existing_provider.cost_usd = cost_usd
                    else:
                        existing_provider.cost_usd = round(existing_provider.cost_usd + cost_usd, 8)

        return models, provider_map, total_cost_usd, interactions_from_models

    def _build_projects_from_rows(
        project_rows: list[dict[str, Any]],
        project_model_rows: list[dict[str, Any]],
        source_id: str,
    ) -> list[ProjectUsage]:
        project_id_map = {
            str(row["project_id"]): _canonical_project_id(
                str(row["project_id"]),
                str(row["project_path"]) if row["project_path"] is not None else None,
            )
            for row in project_rows
        }
        project_cost_map: dict[str, float] = {}
        for row in project_model_rows:
            pid = project_id_map.get(str(row["project_id"]), str(row["project_id"]))
            pricing = pricing_book.get(
                _canonical_model_id(str(row["model_id"]), row["provider_id"])
            )
            if pricing is None:
                continue
            cost = calculate_usage_cost(_token_usage_from_row(row), pricing)
            project_cost_map[pid] = project_cost_map.get(pid, 0.0) + cost

        projects: list[ProjectUsage] = []
        for row in project_rows:
            pid = project_id_map[str(row["project_id"])]
            project_cost = project_cost_map.get(pid)
            projects.append(
                ProjectUsage(
                    project_id=pid,
                    project_name=str(row["project_name"]),
                    project_path=str(row["project_path"])
                    if row["project_path"] is not None
                    else None,
                    usage=_token_usage_from_row(row),
                    total_sessions=int(row["total_sessions"]),
                    total_interactions=int(row["total_interactions"]),
                    cost_usd=round(project_cost, 8) if project_cost is not None else None,
                    has_pricing=project_cost is not None,
                    sources=[source_id],
                )
            )
        return projects

    def _build_project_models_from_rows(
        project_model_rows: list[dict[str, Any]],
        project_rows: list[dict[str, Any]],
    ) -> list[ProjectModelUsage]:
        project_id_map = {
            str(row["project_id"]): _canonical_project_id(
                str(row["project_id"]),
                str(row["project_path"]) if row["project_path"] is not None else None,
            )
            for row in project_rows
        }
        project_models_map: dict[tuple[str, str], ProjectModelUsage] = {}
        for row in project_model_rows:
            pid = project_id_map.get(str(row["project_id"]), str(row["project_id"]))
            mid = _canonical_model_id(str(row["model_id"]), row["provider_id"])
            usage = _token_usage_from_row(row)
            pricing = pricing_book.get(mid)
            cost_usd: float | None = None
            if pricing is not None:
                cost_usd = round(calculate_usage_cost(usage, pricing), 8)
            provider = provider_from_model_id_and_provider_field(mid, row["provider_id"])
            key = (pid, mid)
            existing = project_models_map.get(key)
            if existing is None:
                project_models_map[key] = ProjectModelUsage(
                    project_id=pid,
                    model_id=mid,
                    provider=provider,
                    usage=usage,
                    total_interactions=int(row["total_interactions"]),
                    cost_usd=cost_usd,
                    has_pricing=pricing is not None,
                )
            else:
                existing.usage.input_tokens += usage.input_tokens
                existing.usage.output_tokens += usage.output_tokens
                existing.usage.cache_read_tokens += usage.cache_read_tokens
                existing.usage.cache_write_tokens += usage.cache_write_tokens
                existing.total_interactions += int(row["total_interactions"])
                if cost_usd is not None:
                    existing.has_pricing = True
                    if existing.cost_usd is None:
                        existing.cost_usd = cost_usd
                    else:
                        existing.cost_usd = round(existing.cost_usd + cost_usd, 8)
        return list(project_models_map.values())

    def _build_sessions_from_rows(
        session_model_rows: list[dict[str, Any]],
    ) -> list[SessionUsage]:
        session_map: dict[str, SessionUsage] = {}
        for row in session_model_rows:
            sid = str(row["session_id"])
            mid = _canonical_model_id(str(row["model_id"]), row["provider_id"])
            usage = _token_usage_from_row(row)
            pricing = pricing_book.get(mid)
            model_cost: float | None = None
            if pricing is not None:
                model_cost = round(calculate_usage_cost(usage, pricing), 8)
            provider = provider_from_model_id_and_provider_field(mid, row["provider_id"])
            sm = SessionModelUsage(
                model_id=mid,
                provider=provider,
                usage=usage,
                total_interactions=int(row["total_interactions"]),
                cost_usd=model_cost,
                has_pricing=pricing is not None,
            )
            existing = session_map.get(sid)
            if existing is None:
                started_ms = row["started_at_ms"]
                started_at_val: str | None = None
                if started_ms is not None and int(started_ms) > 0:
                    started_at_val = datetime.fromtimestamp(
                        int(started_ms) / 1000, tz=UTC
                    ).isoformat()
                session_map[sid] = SessionUsage(
                    session_id=sid,
                    title=str(row["session_title"]) if row["session_title"] else None,
                    project_id=str(row["project_id"]) if row["project_id"] else None,
                    project_name=str(row["project_name"]) if row["project_name"] else None,
                    models=[sm],
                    total_tokens=usage.total_tokens,
                    total_interactions=int(row["total_interactions"]),
                    cost_usd=model_cost,
                    has_pricing=pricing is not None,
                    started_at=started_at_val,
                    started_at_ms=started_ms,
                )
            else:
                existing_model = next((m for m in existing.models if m.model_id == mid), None)
                if existing_model is None:
                    existing.models.append(sm)
                else:
                    existing_model.usage.input_tokens += usage.input_tokens
                    existing_model.usage.output_tokens += usage.output_tokens
                    existing_model.usage.cache_read_tokens += usage.cache_read_tokens
                    existing_model.usage.cache_write_tokens += usage.cache_write_tokens
                    existing_model.total_interactions += int(row["total_interactions"])
                    if model_cost is not None:
                        existing_model.has_pricing = True
                        if existing_model.cost_usd is None:
                            existing_model.cost_usd = model_cost
                        else:
                            existing_model.cost_usd = round(existing_model.cost_usd + model_cost, 8)
                existing.total_tokens += usage.total_tokens
                existing.total_interactions += int(row["total_interactions"])
                if model_cost is not None:
                    existing.has_pricing = True
                    if existing.cost_usd is None:
                        existing.cost_usd = model_cost
                    else:
                        existing.cost_usd = round(existing.cost_usd + model_cost, 8)
                row_ms = row["started_at_ms"]
                if row_ms is not None and int(row_ms) > 0 and existing.started_at is not None:
                    candidate = datetime.fromtimestamp(int(row_ms) / 1000, tz=UTC).isoformat()
                    if candidate < existing.started_at:
                        existing.started_at = candidate
                        existing.started_at_ms = int(row_ms)
        return sorted(session_map.values(), key=lambda s: s.total_tokens, reverse=True)

    if len(local_repos) == 1:
        source_id, repository = local_repos[0]
        (
            summary_row,
            model_rows,
            project_rows,
            project_model_rows,
            session_model_rows,
            _use_steps,
            total_interactions,
        ) = _build_date_insights(repository, source_id)

        models, provider_map, total_cost_usd, _ = _build_models_from_rows(model_rows)
        models.sort(key=lambda item: item.usage.total_tokens, reverse=True)
        providers = sorted(
            provider_map.values(), key=lambda item: item.usage.total_tokens, reverse=True
        )
        projects = _build_projects_from_rows(project_rows, project_model_rows, source_id)
        projects.sort(
            key=lambda item: item.cost_usd if item.cost_usd is not None else -1, reverse=True
        )
        project_models = _build_project_models_from_rows(project_model_rows, project_rows)
        project_models.sort(key=lambda item: item.usage.total_tokens, reverse=True)
        sessions = _build_sessions_from_rows(session_model_rows)

        return DateInsightsResponse(
            day=day,
            timezone_offset_minutes=timezone_offset_minutes,
            usage=_token_usage_from_row(summary_row),
            total_sessions=int(summary_row["total_sessions"]),
            total_interactions=total_interactions,
            cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
            pricing_source=pricing_source,
            models=models,
            providers=providers,
            projects=projects,
            project_models=project_models,
            sessions=sessions,
            source_scope=source_scope.kind.value if source_scope else "local",
            sources_considered=[source_id],
            sources_succeeded=[source_id],
            sources_failed=[],
        )

    merged_usage = TokenUsage()
    merged_total_sessions = 0
    merged_total_interactions = 0
    all_model_rows: list[dict[str, Any]] = []
    all_project_rows: list[dict[str, Any]] = []
    all_project_model_rows: list[dict[str, Any]] = []
    all_session_model_rows: list[dict[str, Any]] = []
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
            (
                summary_row,
                model_rows,
                project_rows,
                project_model_rows,
                session_model_rows,
                _use_steps,
                repo_interactions,
            ) = _build_date_insights(repository, source_id)
            merged_usage.input_tokens += int(summary_row["input_tokens"])
            merged_usage.output_tokens += int(summary_row["output_tokens"])
            merged_usage.cache_read_tokens += int(
                summary_row.get("cache_read_tokens", summary_row.get("cache_read", 0))
            )
            merged_usage.cache_write_tokens += int(
                summary_row.get("cache_write_tokens", summary_row.get("cache_write", 0))
            )
            merged_total_sessions += int(summary_row["total_sessions"])
            merged_total_interactions += repo_interactions
            all_model_rows.extend(model_rows)
            all_project_rows.extend(project_rows)
            all_project_model_rows.extend(project_model_rows)
            all_session_model_rows.extend(
                [
                    {
                        **row,
                        "session_id": f"{source_id}:{row['session_id']}",
                    }
                    for row in session_model_rows
                ]
            )
            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    models, provider_map, total_cost_usd, _ = _build_models_from_rows(all_model_rows)
    models.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    providers = sorted(
        provider_map.values(), key=lambda item: item.usage.total_tokens, reverse=True
    )

    def _deduplicate_projects(rows: list[ProjectUsage]) -> list[ProjectUsage]:
        merged: dict[str, ProjectUsage] = {}
        for row in rows:
            key = row.project_path or row.project_id
            existing = merged.get(key)
            if existing is None:
                merged[key] = row
            else:
                merged[key] = merge_project_usage(existing, row)
        return sorted(merged.values(), key=lambda item: item.usage.total_tokens, reverse=True)

    projects = _deduplicate_projects(
        _build_projects_from_rows(all_project_rows, all_project_model_rows, "local")
    )
    projects.sort(key=lambda item: item.cost_usd if item.cost_usd is not None else -1, reverse=True)
    project_models = _build_project_models_from_rows(all_project_model_rows, all_project_rows)
    project_models.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    sessions = _build_sessions_from_rows(all_session_model_rows)

    return DateInsightsResponse(
        day=day,
        timezone_offset_minutes=timezone_offset_minutes,
        usage=merged_usage,
        total_sessions=merged_total_sessions,
        total_interactions=merged_total_interactions,
        cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
        pricing_source=pricing_source,
        models=models,
        providers=providers,
        projects=projects,
        project_models=project_models,
        sessions=sessions,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
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
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
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
            pricing_file_override=pricing_file_override,
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
            pricing_file_override=pricing_file_override,
        )
        return result
    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    def _filter_rows(rows: list[Any]) -> list[Any]:
        if provider is None:
            return rows
        filtered_rows: list[Any] = []
        for row in rows:
            model_id = str(row["model_id"])
            provider_id = row["provider_id"]
            if provider_from_model_id_and_provider_field(model_id, provider_id) == provider:
                filtered_rows.append(row)
        return filtered_rows

    def _build_model_usage_rows(rows: list[Any]) -> tuple[list[ModelUsage], float | None, int]:
        usage_rows: list[ModelUsage] = []
        total_cost_usd: float | None = 0.0 if pricing_book else None
        priced_models = 0

        for row in rows:
            model_id = _canonical_model_id(str(row["model_id"]), row["provider_id"])
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
                    provider=provider_from_model_id_and_provider_field(
                        model_id, row["provider_id"]
                    ),
                    usage=usage,
                    total_sessions=int(row["total_sessions"]),
                    total_interactions=int(row["total_interactions"]),
                    cost_usd=cost_usd,
                    has_pricing=has_pricing,
                )
            )

        return usage_rows, total_cost_usd, priced_models

    if len(local_repos) == 1:
        source_id, repository = local_repos[0]
        rows = _filter_rows(repository.fetch_model_usage_detail(days=days))

        if provider is not None:
            totals = TokenUsage(
                input_tokens=sum(int(r["input_tokens"]) for r in rows),
                output_tokens=sum(int(r["output_tokens"]) for r in rows),
                cache_read_tokens=sum(int(r["cache_read"]) for r in rows),
                cache_write_tokens=sum(int(r["cache_write"]) for r in rows),
            )
            total_sessions = sum(int(r["total_sessions"]) for r in rows)
        else:
            summary_row = _resolved_summary_row(
                repository,
                days=days,
                token_source=token_source,
            )
            totals = _token_usage_from_row(summary_row)
            total_sessions = _resolved_total_sessions(
                repository,
                days=days,
                session_count_source=session_count_source,
                summary_row=summary_row,
            )

        usage_rows, total_cost_usd, priced_models = _build_model_usage_rows(rows)
        total_models = len(usage_rows)
        paged_rows = _paginate_rows(usage_rows, offset=offset, limit=limit)

        return ModelsResponse(
            window_days=days,
            models_offset=offset,
            models_limit=limit if limit > 0 else None,
            models_returned=len(paged_rows),
            total_models=total_models,
            totals=totals,
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
            pricing_source=pricing_source,
            priced_models=priced_models,
            unpriced_models=max(0, len(rows) - priced_models),
            models=paged_rows,
            source_scope=source_scope.kind.value if source_scope else "local",
            sources_considered=[source_id],
            sources_succeeded=[source_id],
            sources_failed=[],
        )

    merged_rows: list[ModelUsage] = []
    merged_totals = TokenUsage()
    merged_total_sessions = 0
    merged_total_cost = 0.0
    has_cost = False
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
            rows = _filter_rows(repository.fetch_model_usage_detail(days=days))
            if provider is not None:
                repo_totals = TokenUsage(
                    input_tokens=sum(int(r["input_tokens"]) for r in rows),
                    output_tokens=sum(int(r["output_tokens"]) for r in rows),
                    cache_read_tokens=sum(int(r["cache_read"]) for r in rows),
                    cache_write_tokens=sum(int(r["cache_write"]) for r in rows),
                )
                repo_total_sessions = sum(int(r["total_sessions"]) for r in rows)
            else:
                repo_summary_row = _resolved_summary_row(
                    repository,
                    days=days,
                    token_source=token_source,
                )
                repo_totals = _token_usage_from_row(repo_summary_row)
                repo_total_sessions = _resolved_total_sessions(
                    repository,
                    days=days,
                    session_count_source=session_count_source,
                    summary_row=repo_summary_row,
                )

            repo_usage_rows, repo_total_cost, _ = _build_model_usage_rows(rows)
            merged_rows = _merge_model_rows(merged_rows, repo_usage_rows)
            merged_totals = merge_token_usage(merged_totals, repo_totals)
            merged_total_sessions += repo_total_sessions
            if repo_total_cost is not None:
                merged_total_cost += repo_total_cost
                has_cost = True
            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    merged_rows.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    paged_rows = _paginate_rows(merged_rows, offset=offset, limit=limit)
    priced_models = sum(1 for item in merged_rows if item.has_pricing)

    return ModelsResponse(
        window_days=days,
        models_offset=offset,
        models_limit=limit if limit > 0 else None,
        models_returned=len(paged_rows),
        total_models=len(merged_rows),
        totals=merged_totals,
        total_sessions=merged_total_sessions,
        total_cost_usd=round(merged_total_cost, 8) if has_cost else None,
        pricing_source=pricing_source,
        priced_models=priced_models,
        unpriced_models=max(0, len(merged_rows) - priced_models),
        models=paged_rows,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
    )


def get_providers(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    offset: int = 0,
    limit: int = 20,
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
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
            pricing_file_override=pricing_file_override,
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
            pricing_file_override=pricing_file_override,
        )
        return result
    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    def _build_provider_rows(model_rows: list[Any]) -> tuple[list[ProviderUsage], float | None]:
        provider_map: dict[str, tuple[ProviderUsage, set[str]]] = {}
        total_cost_usd: float | None = 0.0 if pricing_book else None

        for row in model_rows:
            model_id = _canonical_model_id(str(row["model_id"]), row["provider_id"])
            provider_id = row["provider_id"]
            provider_name = provider_from_model_id_and_provider_field(model_id, provider_id)
            usage = _token_usage_from_row(row)

            model_cost: float | None = None
            pricing = pricing_book.get(model_id)
            if pricing is not None:
                model_cost = round(calculate_usage_cost(usage, pricing), 8)
                if total_cost_usd is not None:
                    total_cost_usd += model_cost

            existing = provider_map.get(provider_name)
            if existing is None:
                provider_map[provider_name] = (
                    ProviderUsage(
                        provider=provider_name,
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
                    ),
                    {model_id},
                )
                continue

            prov_usage, seen_models = existing
            if model_id not in seen_models:
                seen_models.add(model_id)
                prov_usage.total_models += 1
            prov_usage.usage.input_tokens += usage.input_tokens
            prov_usage.usage.output_tokens += usage.output_tokens
            prov_usage.usage.cache_read_tokens += usage.cache_read_tokens
            prov_usage.usage.cache_write_tokens += usage.cache_write_tokens
            prov_usage.total_interactions += int(row["total_interactions"])
            if model_cost is not None:
                prov_usage.has_pricing = True
                if prov_usage.cost_usd is None:
                    prov_usage.cost_usd = model_cost
                else:
                    prov_usage.cost_usd = round(prov_usage.cost_usd + model_cost, 8)

        provider_rows = sorted(
            (p for p, _ in provider_map.values()),
            key=lambda item: item.usage.total_tokens,
            reverse=True,
        )
        return provider_rows, total_cost_usd

    if len(local_repos) == 1:
        source_id, repository = local_repos[0]
        model_rows = repository.fetch_model_usage_detail(days=days)
        summary_row = _resolved_summary_row(
            repository,
            days=days,
            token_source=token_source,
        )
        total_sessions = _resolved_total_sessions(
            repository,
            days=days,
            session_count_source=session_count_source,
            summary_row=summary_row,
        )
        provider_rows, total_cost_usd = _build_provider_rows(model_rows)
        total_providers = len(provider_rows)
        paged_rows = _paginate_rows(provider_rows, offset=offset, limit=limit)

        return ProvidersResponse(
            window_days=days,
            providers_offset=offset,
            providers_limit=limit if limit > 0 else None,
            providers_returned=len(paged_rows),
            total_providers=total_providers,
            totals=_token_usage_from_row(summary_row),
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
            pricing_source=pricing_source,
            providers=paged_rows,
            source_scope=source_scope.kind.value if source_scope else "local",
            sources_considered=[source_id],
            sources_succeeded=[source_id],
            sources_failed=[],
        )

    merged_totals = TokenUsage()
    merged_total_sessions = 0
    merged_total_cost = 0.0
    has_cost = False
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []
    seen_provider_models: dict[str, set[str]] = {}
    merged_provider_rows: list[ProviderUsage] = []

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
            model_rows = repository.fetch_model_usage_detail(days=days)
            deduped_rows: list[dict[str, Any]] = []
            for row in model_rows:
                model_id = _canonical_model_id(str(row["model_id"]), row["provider_id"])
                provider_name = provider_from_model_id_and_provider_field(
                    model_id, row["provider_id"]
                )
                if provider_name not in seen_provider_models:
                    seen_provider_models[provider_name] = set()
                if model_id in seen_provider_models[provider_name]:
                    continue
                seen_provider_models[provider_name].add(model_id)
                deduped_rows.append(row)
            repo_provider_rows, repo_total_cost = _build_provider_rows(deduped_rows)
            merged_provider_rows = _merge_provider_rows(merged_provider_rows, repo_provider_rows)
            repo_summary_row = _resolved_summary_row(
                repository,
                days=days,
                token_source=token_source,
            )
            merged_totals = merge_token_usage(
                merged_totals, _token_usage_from_row(repo_summary_row)
            )
            merged_total_sessions += _resolved_total_sessions(
                repository,
                days=days,
                session_count_source=session_count_source,
                summary_row=repo_summary_row,
            )
            if repo_total_cost is not None:
                merged_total_cost += repo_total_cost
                has_cost = True
            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    merged_provider_rows.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    paged_rows = _paginate_rows(merged_provider_rows, offset=offset, limit=limit)

    return ProvidersResponse(
        window_days=days,
        providers_offset=offset,
        providers_limit=limit if limit > 0 else None,
        providers_returned=len(paged_rows),
        total_providers=len(merged_provider_rows),
        totals=merged_totals,
        total_sessions=merged_total_sessions,
        total_cost_usd=round(merged_total_cost, 8) if has_cost else None,
        pricing_source=pricing_source,
        providers=paged_rows,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
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

    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    def _build_model_detail(
        repo: UsageRepository,
    ) -> tuple[dict[str, Any] | None, dict[str, Any] | None, dict[str, Any] | None]:
        requested_model_id = model_id
        row = repo.fetch_model_detail(model_id=requested_model_id, days=days)
        if row is not None and int(row["total_interactions"]) > 0:
            return row, None, None

        if "/" in requested_model_id:
            fallback_model_id = requested_model_id.split("/", maxsplit=1)[1]
            fallback_row = repo.fetch_model_detail(model_id=fallback_model_id, days=days)
            if fallback_row is not None and int(fallback_row["total_interactions"]) > 0:
                return (
                    row,
                    fallback_row,
                    {
                        "model_id": _canonical_model_id(
                            fallback_model_id, fallback_row["provider_id"]
                        ),
                        "repo_model_id": fallback_model_id,
                        "provider_id": fallback_row["provider_id"],
                    },
                )

        canonical_requested_model_id = _canonical_model_id(requested_model_id)
        if canonical_requested_model_id != requested_model_id:
            canonical_row = repo.fetch_model_detail(
                model_id=canonical_requested_model_id, days=days
            )
            if canonical_row is not None and int(canonical_row["total_interactions"]) > 0:
                return (
                    row,
                    canonical_row,
                    {
                        "model_id": canonical_requested_model_id,
                        "repo_model_id": canonical_requested_model_id,
                        "provider_id": canonical_row["provider_id"],
                    },
                )

        if "/" not in requested_model_id:
            prefixed_model_id = _canonical_model_id(requested_model_id)
            if prefixed_model_id != requested_model_id:
                prefixed_row = repo.fetch_model_detail(model_id=prefixed_model_id, days=days)
                if prefixed_row is not None and int(prefixed_row["total_interactions"]) > 0:
                    return (
                        row,
                        prefixed_row,
                        {
                            "model_id": prefixed_model_id,
                            "repo_model_id": prefixed_model_id,
                            "provider_id": prefixed_row["provider_id"],
                        },
                    )

        return row, None, None

    if len(local_repos) == 1:
        source_id, repository = local_repos[0]
        row, fallback_row, fallback_info = _build_model_detail(repository)
        effective_row = fallback_row if fallback_row is not None else row
        effective_model_id = (
            fallback_info["model_id"]
            if fallback_info is not None
            else _canonical_model_id(model_id)
        )
        repo_model_id = fallback_info["repo_model_id"] if fallback_info is not None else model_id

        if effective_row is None:
            raise RuntimeError(f"No data found for model '{model_id}'.")
        if int(effective_row["total_interactions"]) == 0:
            raise RuntimeError(f"No data found for model '{model_id}'.")

        usage = _token_usage_from_row(effective_row)
        daily_rows = repository.fetch_daily_model_detail(model_id=repo_model_id, days=days)
        pricing = pricing_book.get(effective_model_id)
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
            model_id=effective_model_id,
            provider=provider_from_model_id_and_provider_field(
                effective_model_id, effective_row["provider_id"]
            ),
            window_days=days,
            usage=usage,
            total_sessions=int(effective_row["total_sessions"]),
            total_interactions=int(effective_row["total_interactions"]),
            cost_usd=cost_usd,
            pricing_source=pricing_source,
            daily=daily_usage_rows,
            source_scope=source_scope.kind.value if source_scope else "local",
            sources_considered=[source_id],
            sources_succeeded=[source_id],
            sources_failed=[],
        )

    merged_usage = TokenUsage()
    merged_sessions = 0
    merged_interactions = 0
    merged_daily_map: dict[str, TokenUsage] = {}
    merged_daily_sessions_map: dict[str, int] = {}
    merged_daily_cost_map: dict[str, float] = {}
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []
    effective_model_id = model_id
    effective_provider_id: str | None = None

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
            row, fallback_row, fallback_info = _build_model_detail(repository)
            effective_row = fallback_row if fallback_row is not None else row
            if effective_row is None or int(effective_row["total_interactions"]) == 0:
                continue

            repo_model_id = (
                fallback_info["repo_model_id"] if fallback_info is not None else model_id
            )
            repo_effective_model_id = (
                fallback_info["model_id"]
                if fallback_info is not None
                else _canonical_model_id(model_id)
            )
            repo_provider_id = (
                fallback_info.get("provider_id") if fallback_info is not None else None
            )
            if effective_model_id == model_id and fallback_info is not None:
                effective_model_id = repo_effective_model_id
                effective_provider_id = repo_provider_id

            usage = _token_usage_from_row(effective_row)
            merged_usage.input_tokens += usage.input_tokens
            merged_usage.output_tokens += usage.output_tokens
            merged_usage.cache_read_tokens += usage.cache_read_tokens
            merged_usage.cache_write_tokens += usage.cache_write_tokens
            merged_sessions += int(effective_row["total_sessions"])
            merged_interactions += int(effective_row["total_interactions"])

            pricing = pricing_book.get(repo_effective_model_id)
            daily_rows = repository.fetch_daily_model_detail(model_id=repo_model_id, days=days)
            for daily_row in daily_rows:
                day_str = str(daily_row["day"])
                day_usage = _token_usage_from_row(daily_row)
                existing = merged_daily_map.get(day_str)
                if existing is None:
                    merged_daily_map[day_str] = day_usage
                    merged_daily_sessions_map[day_str] = int(daily_row["total_sessions"])
                else:
                    existing.input_tokens += day_usage.input_tokens
                    existing.output_tokens += day_usage.output_tokens
                    existing.cache_read_tokens += day_usage.cache_read_tokens
                    existing.cache_write_tokens += day_usage.cache_write_tokens
                    merged_daily_sessions_map[day_str] += int(daily_row["total_sessions"])
                if pricing is not None:
                    day_cost = calculate_usage_cost(day_usage, pricing)
                    merged_daily_cost_map[day_str] = (
                        merged_daily_cost_map.get(day_str, 0.0) + day_cost
                    )

            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError(f"No data found for model '{model_id}'.")

    if merged_interactions == 0:
        raise RuntimeError(f"No data found for model '{model_id}'.")

    pricing = pricing_book.get(effective_model_id)
    cost_usd = (
        round(calculate_usage_cost(merged_usage, pricing), 8) if pricing is not None else None
    )

    daily_usage_rows: list[DailyUsage] = []
    for day_str in sorted(merged_daily_map.keys()):
        day_usage = merged_daily_map[day_str]
        day_cost = merged_daily_cost_map.get(day_str)
        daily_usage_rows.append(
            DailyUsage(
                day=date.fromisoformat(day_str),
                usage=day_usage,
                total_sessions=merged_daily_sessions_map[day_str],
                cost_usd=round(day_cost, 8) if day_cost is not None else None,
            )
        )

    return ModelDetailResponse(
        model_id=effective_model_id,
        provider=provider_from_model_id_and_provider_field(
            effective_model_id, effective_provider_id
        ),
        window_days=days,
        usage=merged_usage,
        total_sessions=merged_sessions,
        total_interactions=merged_interactions,
        cost_usd=cost_usd,
        pricing_source=pricing_source,
        daily=daily_usage_rows,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
    )


def get_projects(
    *,
    settings: AppSettings,
    days: int | None = None,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    offset: int = 0,
    limit: int = 20,
    token_source: Literal["auto", "message", "steps"] = "auto",
    session_count_source: Literal["auto", "activity", "session"] = "auto",
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
            pricing_file_override=pricing_file_override,
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
            pricing_file_override=pricing_file_override,
        )
        return result
    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    def _build_project_rows(
        rows: list[Any], project_model_rows: list[Any], source_id: str
    ) -> tuple[list[ProjectUsage], float | None]:
        project_id_map = {
            str(row["project_id"]): _canonical_project_id(
                str(row["project_id"]),
                str(row["project_path"]) if row["project_path"] is not None else None,
            )
            for row in rows
        }
        project_cost_map: dict[str, float] = {}
        total_cost_usd: float | None = 0.0 if pricing_book else None

        for row in project_model_rows:
            project_id = project_id_map.get(str(row["project_id"]), str(row["project_id"]))
            model_id = _canonical_model_id(str(row["model_id"]), row["provider_id"])
            pricing = pricing_book.get(model_id)
            if pricing is None:
                continue
            cost = calculate_usage_cost(_token_usage_from_row(row), pricing)
            project_cost_map[project_id] = project_cost_map.get(project_id, 0.0) + cost
            if total_cost_usd is not None:
                total_cost_usd += cost

        usage_rows: list[ProjectUsage] = []
        for row in rows:
            project_id = project_id_map[str(row["project_id"])]
            project_cost = project_cost_map.get(project_id)
            usage_rows.append(
                ProjectUsage(
                    project_id=project_id,
                    project_name=str(row["project_name"]),
                    project_path=str(row["project_path"])
                    if row["project_path"] is not None
                    else None,
                    usage=_token_usage_from_row(row),
                    total_sessions=int(row["total_sessions"]),
                    total_interactions=int(row["total_interactions"]),
                    cost_usd=round(project_cost, 8) if project_cost is not None else None,
                    has_pricing=project_cost is not None,
                    sources=[source_id],
                )
            )
        return usage_rows, total_cost_usd

    if len(local_repos) == 1:
        source_id, repository = local_repos[0]
        rows = repository.fetch_project_usage_detail(days=days)
        summary_row = _resolved_summary_row(
            repository,
            days=days,
            token_source=token_source,
        )
        total_sessions = _resolved_total_sessions(
            repository,
            days=days,
            session_count_source=session_count_source,
            summary_row=summary_row,
        )
        usage_rows, total_cost_usd = _build_project_rows(
            rows, repository.fetch_project_model_usage(days=days), source_id
        )
        paged_rows = _paginate_rows(usage_rows, offset=offset, limit=limit)

        return ProjectsResponse(
            window_days=days,
            projects_offset=offset,
            projects_limit=limit if limit > 0 else None,
            projects_returned=len(paged_rows),
            total_projects=len(usage_rows),
            totals=_token_usage_from_row(summary_row),
            total_sessions=total_sessions,
            total_cost_usd=round(total_cost_usd, 8) if total_cost_usd is not None else None,
            pricing_source=pricing_source,
            projects=paged_rows,
            source_scope=source_scope.kind.value if source_scope else "local",
            sources_considered=[source_id],
            sources_succeeded=[source_id],
            sources_failed=[],
        )

    merged_project_rows: list[ProjectUsage] = []
    merged_totals = TokenUsage()
    merged_total_sessions = 0
    merged_total_cost = 0.0
    has_cost = False
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
            repo_project_rows, repo_total_cost = _build_project_rows(
                repository.fetch_project_usage_detail(days=days),
                repository.fetch_project_model_usage(days=days),
                source_id,
            )
            merged_project_rows = _merge_project_rows(merged_project_rows, repo_project_rows)
            repo_summary_row = _resolved_summary_row(
                repository,
                days=days,
                token_source=token_source,
            )
            merged_totals = merge_token_usage(
                merged_totals, _token_usage_from_row(repo_summary_row)
            )
            merged_total_sessions += _resolved_total_sessions(
                repository,
                days=days,
                session_count_source=session_count_source,
                summary_row=repo_summary_row,
            )
            if repo_total_cost is not None:
                merged_total_cost += repo_total_cost
                has_cost = True
            sources_succeeded.append(source_id)
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        raise RuntimeError("No local data sources available.")

    merged_project_rows.sort(key=lambda item: item.usage.total_tokens, reverse=True)
    paged_rows = _paginate_rows(merged_project_rows, offset=offset, limit=limit)

    return ProjectsResponse(
        window_days=days,
        projects_offset=offset,
        projects_limit=limit if limit > 0 else None,
        projects_returned=len(paged_rows),
        total_projects=len(merged_project_rows),
        totals=merged_totals,
        total_sessions=merged_total_sessions,
        total_cost_usd=round(merged_total_cost, 8) if has_cost else None,
        pricing_source=pricing_source,
        projects=paged_rows,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
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

    local_repos = _resolve_local_repositories(settings, db_path_override)
    if not local_repos:
        raise RuntimeError("No local data sources found. Run `modelmeter doctor` for details.")

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    def _resolve_repo_project_row(
        repo: UsageRepository,
        *,
        requested_project_id: str,
        known_project_path: str | None,
    ) -> dict[str, Any] | None:
        for row in repo.fetch_project_usage_detail(days=days):
            row_project_id = str(row["project_id"])
            row_project_path = str(row["project_path"]) if row["project_path"] is not None else None
            canonical_project_id = _canonical_project_id(row_project_id, row_project_path)
            if (
                row_project_id == requested_project_id
                or canonical_project_id == requested_project_id
            ):
                return row
            if known_project_path is not None and row_project_path == known_project_path:
                return row
        return None

    def _build_project_detail(
        repo: UsageRepository, source_id: str, known_project_path: str | None = None
    ) -> tuple[list[ProjectSessionUsage], float | None, TokenUsage, int, str, str | None]:
        resolved_project_row = _resolve_repo_project_row(
            repo,
            requested_project_id=project_id,
            known_project_path=known_project_path,
        )
        resolved_project_id = project_id
        if resolved_project_row is not None:
            resolved_project_id = str(resolved_project_row["project_id"])

        session_rows = repo.fetch_project_session_usage(project_id=resolved_project_id, days=days)
        if not session_rows:
            raise RuntimeError(f"No data found for project '{project_id}'.")

        session_model_rows = repo.fetch_project_session_model_usage(
            project_id=resolved_project_id, days=days
        )

        session_cost_map: dict[str, float] = {}
        total_cost_usd: float | None = 0.0 if pricing_book else None
        for row in session_model_rows:
            sid = str(row["session_id"])
            model_id = _canonical_model_id(str(row["model_id"]), row.get("provider_id"))
            pricing = pricing_book.get(model_id)
            if pricing is None:
                continue

            cost = calculate_usage_cost(_token_usage_from_row(row), pricing)
            session_cost_map[sid] = session_cost_map.get(sid, 0.0) + cost
            if total_cost_usd is not None:
                total_cost_usd += cost

        sessions: list[ProjectSessionUsage] = []
        agg_usage = TokenUsage()
        interactions = 0
        for row in session_rows:
            sid = str(row["session_id"])
            usage = _token_usage_from_row(row)
            interactions += int(row["total_interactions"])
            agg_usage.input_tokens += usage.input_tokens
            agg_usage.output_tokens += usage.output_tokens
            agg_usage.cache_read_tokens += usage.cache_read_tokens
            agg_usage.cache_write_tokens += usage.cache_write_tokens

            session_cost = session_cost_map.get(sid)
            sessions.append(
                ProjectSessionUsage(
                    session_id=sid,
                    title=str(row["title"]) if row["title"] is not None else None,
                    directory=str(row["directory"]) if row["directory"] is not None else None,
                    last_updated_ms=int(row["last_updated_ms"]),
                    usage=usage,
                    total_interactions=int(row["total_interactions"]),
                    cost_usd=round(session_cost, 8) if session_cost is not None else None,
                    has_pricing=session_cost is not None,
                )
            )

        first_row = session_rows[0]
        proj_name = str(first_row["project_name"])
        proj_path = (
            str(first_row["project_path"]) if first_row["project_path"] is not None else None
        )
        return sessions, total_cost_usd, agg_usage, interactions, proj_name, proj_path

    if len(local_repos) == 1:
        source_id, repository = local_repos[0]
        (
            repo_sessions,
            total_cost_usd,
            aggregate_usage,
            total_interactions,
            project_name,
            project_path,
        ) = _build_project_detail(repository, source_id)
        total_sessions = len(repo_sessions)
        sliced_sessions = repo_sessions[session_offset:]
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
            sources_considered=[source_id],
            sources_succeeded=[source_id],
            sources_failed=[],
        )

    merged_sessions: list[ProjectSessionUsage] = []
    merged_usage = TokenUsage()
    merged_total_interactions = 0
    merged_total_cost = 0.0
    has_cost = False
    sources_considered: list[str] = []
    sources_succeeded: list[str] = []
    sources_failed: list[dict[str, str]] = []
    project_name: str = project_id
    project_path: str | None = None
    _name_set = False

    not_found_error: str | None = None

    for source_id, repository in local_repos:
        sources_considered.append(source_id)
        try:
            repo_sessions, repo_cost, repo_usage, repo_interactions, repo_name, repo_path = (
                _build_project_detail(repository, source_id, project_path)
            )
            for session in repo_sessions:
                merged_sessions.append(
                    ProjectSessionUsage(
                        session_id=f"{source_id}:{session.session_id}",
                        title=session.title,
                        directory=session.directory,
                        last_updated_ms=session.last_updated_ms,
                        usage=session.usage,
                        total_interactions=session.total_interactions,
                        cost_usd=session.cost_usd,
                        has_pricing=session.has_pricing,
                    )
                )
            merged_usage.input_tokens += repo_usage.input_tokens
            merged_usage.output_tokens += repo_usage.output_tokens
            merged_usage.cache_read_tokens += repo_usage.cache_read_tokens
            merged_usage.cache_write_tokens += repo_usage.cache_write_tokens
            merged_total_interactions += repo_interactions
            if repo_cost is not None:
                merged_total_cost += repo_cost
                has_cost = True
            if not _name_set:
                project_name = repo_name
                project_path = repo_path
                _name_set = True
            sources_succeeded.append(source_id)
        except RuntimeError as exc:
            msg = str(exc)
            if "No data found for project" in msg:
                not_found_error = msg
            sources_failed.append({"source_id": source_id, "error": msg})
        except Exception as exc:
            sources_failed.append({"source_id": source_id, "error": str(exc)})

    if not sources_succeeded:
        if not_found_error:
            raise RuntimeError(not_found_error)
        raise RuntimeError("No local data sources available.")

    total_sessions = len(merged_sessions)
    merged_sessions.sort(key=lambda s: s.last_updated_ms, reverse=True)
    sliced_sessions = merged_sessions[session_offset:]
    if session_limit is not None:
        sliced_sessions = sliced_sessions[:session_limit]

    return ProjectDetailResponse(
        project_id=project_id,
        project_name=project_name or project_id,
        project_path=project_path,
        window_days=days,
        usage=merged_usage,
        total_sessions=total_sessions,
        sessions_offset=session_offset,
        sessions_limit=session_limit,
        sessions_returned=len(sliced_sessions),
        total_interactions=merged_total_interactions,
        total_cost_usd=round(merged_total_cost, 8) if has_cost else None,
        pricing_source=pricing_source,
        sessions=sliced_sessions,
        source_scope="local",
        sources_considered=sources_considered,
        sources_succeeded=sources_succeeded,
        sources_failed=sources_failed,
    )
