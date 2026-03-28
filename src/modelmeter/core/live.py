from __future__ import annotations

import os
import time
from pathlib import Path
from typing import Any, Literal

from modelmeter.config.settings import AppSettings
from modelmeter.core.doctor import generate_doctor_report
from modelmeter.core.models import (
    LiveActiveSession,
    LiveModelUsage,
    LiveSnapshotResponse,
    LiveToolUsage,
    TokenUsage,
)
from modelmeter.core.pricing import calculate_usage_cost, load_pricing_book
from modelmeter.core.sources import SourceScope, SourceScopeKind
from modelmeter.data.jsonl_usage_repository import JsonlUsageRepository
from modelmeter.data.repository import UsageRepository
from modelmeter.data.storage import resolve_storage_paths

ACTIVE_SESSION_THRESHOLD_MS = 10 * 60 * 1000


def _resolve_live_token_source(
    repository: UsageRepository,
    *,
    token_source: Literal["auto", "message", "steps"],
    since_ms: int,
) -> Literal["message", "steps"]:
    if token_source != "auto":
        return token_source

    steps_row = repository.fetch_live_summary_steps(since_ms=since_ms)
    if int(steps_row["total_interactions"]) > 0:
        return "steps"
    return "message"


def _resolve_sqlite_path(settings: AppSettings, db_path_override: Path | None = None) -> Path:
    report = generate_doctor_report(settings=settings, db_path_override=db_path_override)
    if report.selected_source != "sqlite":
        raise RuntimeError(
            "SQLite data source is unavailable or incompatible. "
            "Run `modelmeter doctor` for details."
        )
    paths = resolve_storage_paths(settings, db_path_override=db_path_override)
    return paths.sqlite_db_path


def _token_usage_from_row(row: dict[str, Any]) -> TokenUsage:
    mapping = row
    return TokenUsage(
        input_tokens=int(mapping.get("input_tokens", 0)),
        output_tokens=int(mapping.get("output_tokens", 0)),
        cache_read_tokens=int(mapping.get("cache_read_tokens", mapping.get("cache_read", 0))),
        cache_write_tokens=int(mapping.get("cache_write_tokens", mapping.get("cache_write", 0))),
    )


def get_live_snapshot(
    *,
    settings: AppSettings,
    window_minutes: int = 60,
    db_path_override: Path | None = None,
    pricing_file_override: Path | None = None,
    token_source: Literal["auto", "message", "steps"] = "auto",
    models_limit: int = 5,
    tools_limit: int = 8,
    source_scope: SourceScope | None = None,
    session_id: str | None = None,
) -> LiveSnapshotResponse:
    """Return a live activity snapshot for selected rolling window.

    If session_id is provided, filter to that session only.
    Otherwise, return aggregated data across all sessions.
    """
    if source_scope is not None and source_scope.kind != SourceScopeKind.LOCAL:
        raise NotImplementedError("Federated live analytics not yet implemented")

    now_ms = int(time.time() * 1000)
    since_ms = now_ms - (window_minutes * 60 * 1000)

    repositories = _resolve_live_repositories(
        settings=settings,
        db_path_override=db_path_override,
    )

    return _build_live_snapshot(
        repositories=repositories,
        session_id=session_id,
        settings=settings,
        now_ms=now_ms,
        since_ms=since_ms,
        window_minutes=window_minutes,
        pricing_file_override=pricing_file_override,
        token_source=token_source,
        models_limit=models_limit,
        tools_limit=tools_limit,
    )


def _resolve_live_repositories(
    *,
    settings: AppSettings,
    db_path_override: Path | None,
) -> list[tuple[str, UsageRepository]]:
    from modelmeter.core.analytics import _resolve_local_repositories

    repositories = _resolve_local_repositories(settings, db_path_override)
    if not repositories:
        raise RuntimeError(
            "No local live data source is available. Run `modelmeter doctor` for details."
        )
    return repositories


def _build_live_snapshot(
    *,
    repositories: list[tuple[str, UsageRepository]],
    settings: AppSettings,
    now_ms: int,
    since_ms: int,
    window_minutes: int,
    pricing_file_override: Path | None,
    token_source: Literal["auto", "message", "steps"],
    models_limit: int,
    tools_limit: int,
    session_id: str | None,
) -> LiveSnapshotResponse:
    if session_id is not None:
        requested_source_id: str | None = None
        raw_session_id = session_id
        if ":" in session_id:
            requested_source_id, raw_session_id = session_id.split(":", maxsplit=1)

        for source_id, repository in repositories:
            if requested_source_id is not None and source_id != requested_source_id:
                continue
            row = repository.fetch_active_session(session_id=raw_session_id)
            if row is not None:
                agent = "claudecode" if source_id == "local-claudecode" else "opencode"
                return _build_snapshot_from_single_source(
                    repository=repository,
                    settings=settings,
                    now_ms=now_ms,
                    since_ms=since_ms,
                    window_minutes=window_minutes,
                    pricing_file_override=pricing_file_override,
                    token_source=token_source,
                    models_limit=models_limit,
                    tools_limit=tools_limit,
                    session_id=raw_session_id,
                    agent=agent,
                    public_session_id=session_id,
                )
        raise RuntimeError(f"Live session `{session_id}` was not found.")

    total_summary: dict[str, Any] | None = None
    all_model_rows: list[dict[str, Any]] = []
    all_tool_rows: list[dict[str, Any]] = []
    active_session: LiveActiveSession | None = None
    most_recent_session_ms = 0

    if token_source == "auto" and len(repositories) > 1:
        resolved_token_source: Literal["message", "steps"] = "message"
        for _, repo in repositories:
            if _resolve_live_token_source(repo, token_source="auto", since_ms=since_ms) == "steps":
                resolved_token_source = "steps"
                break
    elif token_source == "auto":
        resolved_token_source = _resolve_live_token_source(
            repositories[0][1],
            token_source="auto",
            since_ms=since_ms,
        )
    else:
        resolved_token_source = token_source

    for source_id, repository in repositories:
        agent = "claudecode" if source_id == "local-claudecode" else "opencode"

        if resolved_token_source == "steps":
            summary = repository.fetch_live_summary_steps(since_ms=since_ms)
        else:
            summary = repository.fetch_live_summary_messages(since_ms=since_ms)

        if total_summary is None:
            total_summary = dict(summary)
        else:
            total_summary["input_tokens"] = int(total_summary.get("input_tokens", 0)) + int(
                summary.get("input_tokens", 0)
            )
            total_summary["output_tokens"] = int(total_summary.get("output_tokens", 0)) + int(
                summary.get("output_tokens", 0)
            )
            total_summary["cache_read"] = int(total_summary.get("cache_read", 0)) + int(
                summary.get("cache_read", 0)
            )
            total_summary["cache_write"] = int(total_summary.get("cache_write", 0)) + int(
                summary.get("cache_write", 0)
            )
            total_summary["total_sessions"] = int(total_summary.get("total_sessions", 0)) + int(
                summary.get("total_sessions", 0)
            )
            total_summary["total_interactions"] = int(
                total_summary.get("total_interactions", 0)
            ) + int(summary.get("total_interactions", 0))

        all_model_rows.extend(repository.fetch_live_model_usage(since_ms=since_ms, limit=9999))
        all_tool_rows.extend(repository.fetch_live_tool_usage(since_ms=since_ms, limit=9999))

        active_row = repository.fetch_active_session(session_id=None)
        if active_row is not None:
            row_ms = int(active_row["time_updated"])
            if row_ms > most_recent_session_ms:
                most_recent_session_ms = row_ms
                active_session = LiveActiveSession(
                    session_id=str(active_row["id"]),
                    title=str(active_row["title"]) if active_row["title"] else None,
                    project_id=str(active_row["project_id"]) if active_row["project_id"] else None,
                    project_name=str(active_row["project_name"])
                    if active_row["project_name"]
                    else None,
                    directory=str(active_row["directory"]) if active_row["directory"] else None,
                    last_updated_ms=row_ms,
                    is_active=(now_ms - row_ms) <= ACTIVE_SESSION_THRESHOLD_MS,
                    agent=agent,
                )

    if total_summary is None:
        total_summary = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cache_read": 0,
            "cache_write": 0,
            "total_sessions": 0,
            "total_interactions": 0,
        }

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    from modelmeter.core.analytics import _canonical_model_id

    model_map: dict[str, dict[str, Any]] = {}
    for row in all_model_rows:
        mid = _canonical_model_id(str(row["model_id"]), row.get("provider_id"))
        if mid not in model_map:
            normalized_row = dict(row)
            normalized_row["model_id"] = mid
            model_map[mid] = normalized_row
        else:
            for key in (
                "input_tokens",
                "output_tokens",
                "cache_read",
                "cache_write",
                "total_sessions",
                "total_interactions",
            ):
                model_map[mid][key] = int(model_map[mid].get(key, 0)) + int(row.get(key, 0))

    top_models: list[LiveModelUsage] = []
    total_cost = 0.0
    has_any_priced_model = False
    for mid, row in sorted(
        model_map.items(),
        key=lambda x: x[1].get("input_tokens", 0) + x[1].get("output_tokens", 0),
        reverse=True,
    )[:models_limit]:
        usage = _token_usage_from_row(row)
        pricing = pricing_book.get(mid)
        model_cost: float | None = None
        if pricing is not None:
            has_any_priced_model = True
            model_cost = round(calculate_usage_cost(usage, pricing), 8)
            total_cost += model_cost
        top_models.append(
            LiveModelUsage(
                model_id=mid,
                usage=usage,
                total_sessions=int(row.get("total_sessions", 0)),
                total_interactions=int(row.get("total_interactions", 0)),
                cost_usd=model_cost,
            )
        )

    tool_map: dict[str, int] = {}
    for row in all_tool_rows:
        tool_map[str(row["tool_name"])] = tool_map.get(row["tool_name"], 0) + int(
            row["total_calls"]
        )

    return LiveSnapshotResponse(
        generated_at_ms=now_ms,
        window_minutes=window_minutes,
        token_source=resolved_token_source,
        total_interactions=int(total_summary.get("total_interactions", 0)),
        total_sessions=int(total_summary.get("total_sessions", 0)),
        usage=_token_usage_from_row(total_summary),
        cost_usd=round(total_cost, 8) if has_any_priced_model else None,
        pricing_source=pricing_source,
        active_session=active_session,
        top_models=top_models,
        top_tools=[
            LiveToolUsage(tool_name=name, total_calls=calls)
            for name, calls in sorted(tool_map.items(), key=lambda x: x[1], reverse=True)[
                :tools_limit
            ]
        ],
    )


def _build_snapshot_from_single_source(
    *,
    repository: UsageRepository,
    settings: AppSettings,
    now_ms: int,
    since_ms: int,
    window_minutes: int,
    pricing_file_override: Path | None,
    token_source: Literal["auto", "message", "steps"],
    models_limit: int,
    tools_limit: int,
    session_id: str | None,
    agent: str,
    public_session_id: str | None = None,
) -> LiveSnapshotResponse:
    resolved_token_source = _resolve_live_token_source(
        repository,
        token_source=token_source,
        since_ms=since_ms,
    )

    summary_row: dict[str, Any]
    if resolved_token_source == "steps":
        summary_row = repository.fetch_live_summary_steps(since_ms=since_ms, session_id=session_id)
    else:
        summary_row = repository.fetch_live_summary_messages(
            since_ms=since_ms, session_id=session_id
        )

    model_rows = repository.fetch_live_model_usage(
        since_ms=since_ms, limit=models_limit, session_id=session_id
    )
    tool_rows = repository.fetch_live_tool_usage(
        since_ms=since_ms, limit=tools_limit, session_id=session_id
    )

    pricing_book, pricing_source = load_pricing_book(
        settings=settings,
        pricing_file_override=pricing_file_override,
    )

    from modelmeter.core.analytics import _canonical_model_id

    top_models: list[LiveModelUsage] = []
    total_cost = 0.0
    has_any_priced_model = False

    for row in model_rows:
        model_id = _canonical_model_id(str(row["model_id"]), row.get("provider_id"))
        usage = _token_usage_from_row(row)
        pricing = pricing_book.get(model_id)
        model_cost: float | None = None
        if pricing is not None:
            has_any_priced_model = True
            model_cost = round(calculate_usage_cost(usage, pricing), 8)
            total_cost += model_cost

        top_models.append(
            LiveModelUsage(
                model_id=model_id,
                usage=usage,
                total_sessions=int(row["total_sessions"]),
                total_interactions=int(row["total_interactions"]),
                cost_usd=model_cost,
            )
        )

    active_session_row = repository.fetch_active_session(session_id=session_id)
    active_session: LiveActiveSession | None = None
    if active_session_row is not None:
        last_updated_ms = int(active_session_row["time_updated"])
        resolved_session_id = (
            public_session_id if public_session_id is not None else str(active_session_row["id"])
        )
        active_session = LiveActiveSession(
            session_id=resolved_session_id,
            title=str(active_session_row["title"])
            if active_session_row["title"] is not None
            else None,
            project_id=str(active_session_row["project_id"])
            if active_session_row["project_id"] is not None
            else None,
            project_name=str(active_session_row["project_name"])
            if active_session_row["project_name"] is not None
            else None,
            directory=str(active_session_row["directory"])
            if active_session_row["directory"] is not None
            else None,
            last_updated_ms=last_updated_ms,
            is_active=(now_ms - last_updated_ms) <= ACTIVE_SESSION_THRESHOLD_MS,
            agent=agent,
        )

    return LiveSnapshotResponse(
        generated_at_ms=now_ms,
        window_minutes=window_minutes,
        token_source=resolved_token_source,
        total_interactions=int(summary_row.get("total_interactions", 0)),
        total_sessions=int(summary_row["total_sessions"]),
        usage=_token_usage_from_row(summary_row),
        cost_usd=round(total_cost, 8) if has_any_priced_model else None,
        pricing_source=pricing_source,
        active_session=active_session,
        top_models=top_models,
        top_tools=[
            LiveToolUsage(
                tool_name=str(row["tool_name"]),
                total_calls=int(row["total_calls"]),
            )
            for row in tool_rows
        ],
    )


def _detect_claudecode_active_sessions(
    settings: AppSettings,
) -> list[LiveActiveSession]:
    """Detect active Claude Code sessions based on JSONL file mtime.

    A session is considered active if its JSONL file was modified
    within the last 10 minutes.
    """
    if not settings.claudecode_enabled:
        return []

    projects_dir = settings.claudecode_data_dir / "projects"
    if not projects_dir.exists():
        return []

    now_ms = int(time.time() * 1000)
    repository = JsonlUsageRepository(settings.claudecode_data_dir)
    sessions: list[LiveActiveSession] = []

    for jsonl_file in projects_dir.rglob("*.jsonl"):
        if "subagents" in jsonl_file.parts:
            continue

        try:
            mtime_ms = int(os.stat(jsonl_file).st_mtime * 1000)
        except OSError:
            continue

        if (now_ms - mtime_ms) > ACTIVE_SESSION_THRESHOLD_MS:
            continue

        active_session_row = repository.fetch_active_session(session_id=jsonl_file.stem)
        if active_session_row is None:
            continue

        sessions.append(
            LiveActiveSession(
                session_id=str(active_session_row["id"]),
                title=str(active_session_row["title"])
                if active_session_row["title"] is not None
                else None,
                project_id=str(active_session_row["project_id"])
                if active_session_row["project_id"] is not None
                else None,
                project_name=str(active_session_row["project_name"])
                if active_session_row["project_name"] is not None
                else None,
                directory=str(active_session_row["directory"])
                if active_session_row["directory"] is not None
                else None,
                last_updated_ms=mtime_ms,
                is_active=True,
                agent="claudecode",
            )
        )

    return sessions


def get_live_sessions(
    *,
    settings: AppSettings,
    db_path_override: Path | None = None,
) -> list[LiveActiveSession]:
    """Return active sessions across all agents (OpenCode and Claude Code).

    For scope=local, resolves all local repositories and queries each for
    active sessions. Each session gets its own snapshot.
    """
    from modelmeter.core.analytics import _resolve_local_repositories

    sessions: list[LiveActiveSession] = []
    now_ms = int(time.time() * 1000)

    repos = _resolve_local_repositories(settings, db_path_override)
    for source_id, repo in repos:
        if source_id == "local-opencode":
            active_row = repo.fetch_active_session()
            if active_row is not None:
                last_updated_ms = int(active_row["time_updated"])
                sessions.append(
                    LiveActiveSession(
                        session_id=str(active_row["id"]),
                        title=str(active_row["title"]) if active_row["title"] else None,
                        project_id=str(active_row["project_id"])
                        if active_row["project_id"]
                        else None,
                        project_name=str(active_row["project_name"])
                        if active_row["project_name"]
                        else None,
                        directory=str(active_row["directory"]) if active_row["directory"] else None,
                        last_updated_ms=last_updated_ms,
                        is_active=(now_ms - last_updated_ms) <= ACTIVE_SESSION_THRESHOLD_MS,
                        agent="opencode",
                    )
                )
        elif source_id == "local-claudecode":
            sessions.extend(_detect_claudecode_active_sessions(settings))

    return sessions
