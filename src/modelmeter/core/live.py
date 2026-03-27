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

    repository = _resolve_live_repository(
        settings=settings,
        db_path_override=db_path_override,
        session_id=session_id,
    )

    return _build_live_snapshot(
        repository=repository,
        settings=settings,
        now_ms=now_ms,
        since_ms=since_ms,
        window_minutes=window_minutes,
        pricing_file_override=pricing_file_override,
        token_source=token_source,
        models_limit=models_limit,
        tools_limit=tools_limit,
        session_id=session_id,
    )


def _resolve_live_repository(
    *,
    settings: AppSettings,
    db_path_override: Path | None,
    session_id: str | None,
) -> UsageRepository:
    from modelmeter.core.analytics import _resolve_local_repositories

    repositories = [repo for _, repo in _resolve_local_repositories(settings, db_path_override)]
    if not repositories:
        raise RuntimeError(
            "No local live data source is available. Run `modelmeter doctor` for details."
        )

    if session_id is not None:
        for repository in repositories:
            if repository.fetch_active_session(session_id=session_id) is not None:
                return repository
        raise RuntimeError(f"Live session `{session_id}` was not found.")

    return repositories[0]


def _build_live_snapshot(
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

    top_models: list[LiveModelUsage] = []
    total_cost = 0.0
    has_any_priced_model = False

    for row in model_rows:
        model_id = str(row["model_id"])
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
        active_session = LiveActiveSession(
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
            last_updated_ms=last_updated_ms,
            is_active=(now_ms - last_updated_ms) <= ACTIVE_SESSION_THRESHOLD_MS,
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
                    )
                )
        elif source_id == "local-claudecode":
            sessions.extend(_detect_claudecode_active_sessions(settings))

    return sessions
