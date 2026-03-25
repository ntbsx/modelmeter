"""Repository protocol and factory for usage data readers."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal, Protocol, runtime_checkable

RowDict = dict[str, Any]


@runtime_checkable
class UsageRepository(Protocol):
    """Protocol for usage data readers (SQLite, JSONL, etc.)."""

    def fetch_summary(self, *, days: int | None = None) -> RowDict: ...
    def fetch_summary_steps(self, *, days: int | None = None) -> RowDict: ...
    def fetch_summary_for_day(self, *, day: str, timezone_offset_minutes: int = 0) -> RowDict: ...
    def fetch_summary_for_day_steps(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> RowDict | None: ...
    def fetch_session_count(self, *, days: int | None = None) -> int: ...
    def fetch_daily(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_daily_steps(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_daily_session_counts(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> dict[str, int]: ...
    def fetch_model_usage(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_model_usage_detail(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_model_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_model_detail(self, *, model_id: str, days: int | None = None) -> RowDict | None: ...
    def fetch_daily_model_detail(
        self, *, model_id: str, days: int | None = None
    ) -> list[RowDict]: ...
    def fetch_daily_model_usage(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_project_usage_detail(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_project_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_project_model_usage(self, *, days: int | None = None) -> list[RowDict]: ...
    def fetch_project_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_session_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]: ...
    def fetch_project_session_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[RowDict]: ...
    def fetch_project_session_model_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[RowDict]: ...
    def fetch_active_session(self, *, session_id: str | None = None) -> RowDict | None: ...
    def fetch_sessions_summary(
        self,
        *,
        limit: int = 20,
        include_archived: bool = False,
        min_time_updated_ms: int | None = None,
    ) -> list[RowDict]: ...
    def fetch_live_summary_messages(
        self, *, since_ms: int, session_id: str | None = None
    ) -> RowDict: ...
    def fetch_live_summary_steps(
        self, *, since_ms: int, session_id: str | None = None
    ) -> RowDict: ...
    def fetch_live_model_usage(
        self, *, since_ms: int, limit: int = 5, session_id: str | None = None
    ) -> list[RowDict]: ...
    def fetch_live_tool_usage(
        self, *, since_ms: int, limit: int = 8, session_id: str | None = None
    ) -> list[RowDict]: ...
    def resolve_token_source(
        self,
        *,
        days: int | None,
        token_source: Literal["auto", "message", "steps"],
    ) -> Literal["message", "steps"]: ...
    def resolve_session_count_source(
        self,
        *,
        days: int | None,
        session_count_source: Literal["auto", "activity", "session"],
    ) -> Literal["activity", "session"]: ...


def create_repository(kind: str, path: Path) -> UsageRepository:
    """Factory function to create the appropriate repository."""
    if kind == "sqlite":
        from modelmeter.data.sqlite_usage_repository import SQLiteUsageRepository

        return SQLiteUsageRepository(path)  # type: ignore[return-value]
    if kind == "jsonl":
        from modelmeter.data.jsonl_usage_repository import JsonlUsageRepository  # type: ignore[import]

        return JsonlUsageRepository(path)  # type: ignore[return-value]
    raise ValueError(f"Unknown repository kind: {kind}")
