"""SQLite-backed usage queries for analytics endpoints."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal


class SQLiteUsageRepository:
    """Read-only usage queries against the OpenCode SQLite database."""

    def __init__(self, db_path: Path):
        self._db_path = db_path
        # Simple per-instance memoization: repository instances are short-lived
        # (one per analytics call), so this avoids redundant queries within a
        # single request without the overhead of TTL bookkeeping.
        self._cache: dict[tuple[str, ...], Any] = {}

    def _connect(self) -> sqlite3.Connection:
        uri = f"file:{self._db_path}?mode=ro"
        connection = sqlite3.connect(uri, uri=True)
        connection.row_factory = sqlite3.Row
        # 64 MB page cache (negative value = kibibytes): reduces page faults on
        # large table scans at the cost of up to 64 MB of process memory.
        connection.execute("PRAGMA cache_size = -64000")
        # 256 MB memory-mapped I/O window: bypasses read() syscall overhead for
        # repeated page access. Adds up to 256 MB of virtual address space; does
        # not pin that much physical RAM unless pages are actually touched.
        connection.execute("PRAGMA mmap_size = 268435456")
        # Keep internal temp tables (sorts, grouping) in RAM instead of a temp
        # file. Safe for read-only connections; bounded by available memory.
        connection.execute("PRAGMA temp_store = MEMORY")
        # NORMAL durability: skips fsync after each write group. Read-only
        # connections are unaffected by this, but it avoids any implicit
        # sync overhead if SQLite ever needs to roll back a read transaction.
        connection.execute("PRAGMA synchronous = NORMAL")
        return connection

    def _cache_key(self, method_name: str, **kwargs: Any) -> tuple[str, ...]:
        parts: list[str] = [method_name]
        for key in sorted(kwargs.keys()):
            value: Any = kwargs[key]
            if value is None:
                parts.append(f"{key}=None")
            elif isinstance(value, (list, tuple)):
                parts.append(f"{key}={','.join(str(v) for v in value)}")  # type: ignore[arg-type]
            else:
                parts.append(f"{key}={value}")
        return tuple(parts)

    def _get_cached(self, key: tuple[str, ...]) -> Any | None:
        return self._cache.get(key)

    def _set_cached(self, key: tuple[str, ...], result: Any) -> None:
        self._cache[key] = result

    @staticmethod
    def _time_filter(days: int | None, *, time_expr: str) -> tuple[str, list[int]]:
        if days is None:
            return "", []

        cutoff = datetime.now(tz=UTC) - timedelta(days=days)
        cutoff_ms = int(cutoff.timestamp() * 1000)
        return (
            f"AND COALESCE({time_expr}, 0) >= ?",
            [cutoff_ms],
        )

    @staticmethod
    def _day_bucket_expr(*, time_expr: str, timezone_offset_minutes: int = 0) -> str:
        if timezone_offset_minutes == 0:
            return f"date({time_expr} / 1000, 'unixepoch')"

        offset_modifier = f"{timezone_offset_minutes:+d} minutes"
        return f"date({time_expr} / 1000, 'unixepoch', '{offset_modifier}')"

    def _target_day_filter(
        self,
        *,
        day: str,
        time_expr: str,
        timezone_offset_minutes: int = 0,
    ) -> tuple[str, list[str]]:
        day_expr = self._day_bucket_expr(
            time_expr=time_expr,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        return f"AND {day_expr} = ?", [day]

    def fetch_summary(self, *, days: int | None = None) -> sqlite3.Row:
        """Fetch aggregate usage totals and distinct session count."""
        cache_key = self._cache_key("fetch_summary", days=days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        query = f"""
            SELECT
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              {time_filter}
        """

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            if row is None:
                raise RuntimeError("Summary query returned no row")
            self._set_cached(cache_key, row)
            return row

    def fetch_session_count(self, *, days: int | None = None) -> int:
        """Fetch count of sessions created in the selected window."""
        cache_key = self._cache_key("fetch_session_count", days=days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(days, time_expr="time_created")
        query = f"""
            SELECT COUNT(*) AS total_sessions
            FROM session
            WHERE 1=1
              {time_filter}
        """

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            result = 0 if row is None else int(row["total_sessions"])
            self._set_cached(cache_key, result)
            return result

    def fetch_summary_for_day(
        self,
        *,
        day: str,
        timezone_offset_minutes: int = 0,
    ) -> sqlite3.Row:
        """Fetch aggregate usage totals for one local day."""
        cache_key = self._cache_key(
            "fetch_summary_for_day",
            day=day,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        day_filter, params = self._target_day_filter(
            day=day,
            time_expr="json_extract(data, '$.time.created')",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(json_extract(data, '$.time.created'), 0) > 0
              {day_filter}
        """

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            if row is None:
                raise RuntimeError("Date summary query returned no row")
            self._set_cached(cache_key, row)
            return row

    def fetch_summary_for_day_steps(
        self,
        *,
        day: str,
        timezone_offset_minutes: int = 0,
    ) -> sqlite3.Row | None:
        """Fetch aggregate usage totals from step-finish parts for one local day."""
        cache_key = self._cache_key(
            "fetch_summary_for_day_steps",
            day=day,
            timezone_offset_minutes=timezone_offset_minutes,
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        day_filter, params = self._target_day_filter(
            day=day,
            time_expr="time_created",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM part
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.type') = 'step-finish'
              {day_filter}
        """

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            if row is None:
                self._set_cached(cache_key, None)
                return None
            self._set_cached(cache_key, row)
            return row

    def fetch_daily_session_counts(
        self,
        *,
        days: int | None = None,
        timezone_offset_minutes: int = 0,
    ) -> dict[str, int]:
        """Fetch sessions created per day in the selected window."""
        time_filter, params = self._time_filter(days, time_expr="time_created")
        day_expr = self._day_bucket_expr(
            time_expr="time_created",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                {day_expr} AS day,
                COUNT(*) AS total_sessions
            FROM session
            WHERE 1=1
              {time_filter}
            GROUP BY day
        """

        with self._connect() as conn:
            rows = conn.execute(query, params).fetchall()

        return {str(row["day"]): int(row["total_sessions"]) for row in rows}

    def fetch_summary_steps(self, *, days: int | None = None) -> sqlite3.Row:
        """Fetch aggregate usage totals from step-finish parts."""
        cache_key = self._cache_key("fetch_summary_steps", days=days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(days, time_expr="time_created")
        query = f"""
            SELECT
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM part
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.type') = 'step-finish'
              {time_filter}
        """

        with self._connect() as conn:
            row = conn.execute(query, params).fetchone()
            if row is None:
                raise RuntimeError("Step summary query returned no row")
            self._set_cached(cache_key, row)
            return row

    def fetch_daily(
        self,
        *,
        days: int | None = None,
        timezone_offset_minutes: int = 0,
    ) -> list[sqlite3.Row]:
        """Fetch daily usage aggregates ordered by day ascending."""
        cache_key = self._cache_key(
            "fetch_daily", days=days, timezone_offset_minutes=timezone_offset_minutes
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        day_expr = self._day_bucket_expr(
            time_expr="json_extract(data, '$.time.created')",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                {day_expr} AS day,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(json_extract(data, '$.time.created'), 0) > 0
              {time_filter}
            GROUP BY day
            ORDER BY day ASC
        """

        with self._connect() as conn:
            result = conn.execute(query, params).fetchall()
            self._set_cached(cache_key, result)
            return result

    def fetch_daily_steps(
        self,
        *,
        days: int | None = None,
        timezone_offset_minutes: int = 0,
    ) -> list[sqlite3.Row]:
        """Fetch daily usage aggregates from step-finish parts."""
        cache_key = self._cache_key(
            "fetch_daily_steps", days=days, timezone_offset_minutes=timezone_offset_minutes
        )
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(days, time_expr="time_created")
        day_expr = self._day_bucket_expr(
            time_expr="time_created",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                {day_expr} AS day,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM part
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.type') = 'step-finish'
              {time_filter}
            GROUP BY day
            ORDER BY day ASC
        """

        with self._connect() as conn:
            result = conn.execute(query, params).fetchall()
            self._set_cached(cache_key, result)
            return result

    def resolve_token_source(
        self,
        *,
        days: int | None,
        token_source: Literal["auto", "message", "steps"],
    ) -> Literal["message", "steps"]:
        """Resolve effective token source for aggregations."""
        if token_source != "auto":
            return token_source

        summary = self.fetch_summary_steps(days=days)
        if int(summary["total_sessions"]) > 0:
            return "steps"
        return "message"

    def resolve_session_count_source(
        self,
        *,
        days: int | None,
        session_count_source: Literal["auto", "activity", "session"],
    ) -> Literal["activity", "session"]:
        """Resolve effective session counting source."""
        if session_count_source != "auto":
            return session_count_source

        try:
            self.fetch_session_count(days=days)
        except sqlite3.Error:
            return "activity"
        return "session"

    def fetch_model_usage(self, *, days: int | None = None) -> list[sqlite3.Row]:
        """Fetch token usage grouped by model."""
        cache_key = self._cache_key("fetch_model_usage", days=days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        query = f"""
            SELECT
                COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              {time_filter}
            GROUP BY model_id
        """

        with self._connect() as conn:
            result = conn.execute(query, params).fetchall()
            self._set_cached(cache_key, result)
            return result

    def fetch_daily_model_usage(
        self,
        *,
        days: int | None = None,
        timezone_offset_minutes: int = 0,
    ) -> list[sqlite3.Row]:
        """Fetch token usage grouped by day and model."""
        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        day_expr = self._day_bucket_expr(
            time_expr="json_extract(data, '$.time.created')",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                {day_expr} AS day,
                COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(data, '$.providerID'),
                    json_extract(data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(json_extract(data, '$.time.created'), 0) > 0
              {time_filter}
            GROUP BY day, model_id, provider_id
            ORDER BY day ASC
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_model_usage_detail(self, *, days: int | None = None) -> list[sqlite3.Row]:
        """Fetch usage grouped by model with interactions and session counts."""
        cache_key = self._cache_key("fetch_model_usage_detail", days=days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        query = f"""
            SELECT
                COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(data, '$.providerID'),
                    json_extract(data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              {time_filter}
            GROUP BY model_id, provider_id
            ORDER BY input_tokens + output_tokens + cache_read + cache_write DESC
        """

        with self._connect() as conn:
            result = conn.execute(query, params).fetchall()
            self._set_cached(cache_key, result)
            return result

    def fetch_model_usage_detail_for_day(
        self,
        *,
        day: str,
        timezone_offset_minutes: int = 0,
    ) -> list[sqlite3.Row]:
        """Fetch usage grouped by model for one local day."""
        day_filter, params = self._target_day_filter(
            day=day,
            time_expr="json_extract(data, '$.time.created')",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(data, '$.providerID'),
                    json_extract(data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(json_extract(data, '$.time.created'), 0) > 0
              {day_filter}
            GROUP BY model_id, provider_id
            ORDER BY input_tokens + output_tokens + cache_read + cache_write DESC
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_model_detail(self, *, model_id: str, days: int | None = None) -> sqlite3.Row | None:
        """Fetch aggregate usage detail for one model."""
        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        params = [model_id, *params]
        query = f"""
            SELECT
                MAX(COALESCE(
                    json_extract(data, '$.providerID'),
                    json_extract(data, '$.model.providerID'),
                    NULL
                )) AS provider_id,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
              ) = ?
              {time_filter}
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchone()

    def fetch_daily_model_detail(
        self, *, model_id: str, days: int | None = None
    ) -> list[sqlite3.Row]:
        """Fetch daily usage detail for one model."""
        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(data, '$.time.created')",
        )
        params = [model_id, *params]
        query = f"""
            SELECT
                date(json_extract(data, '$.time.created') / 1000, 'unixepoch') AS day,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
              ) = ?
              AND COALESCE(json_extract(data, '$.time.created'), 0) > 0
              {time_filter}
            GROUP BY day
            ORDER BY day ASC
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_project_usage_detail(self, *, days: int | None = None) -> list[sqlite3.Row]:
        """Fetch usage grouped by project with interactions and session counts."""
        cache_key = self._cache_key("fetch_project_usage_detail", days=days)
        cached = self._get_cached(cache_key)
        if cached is not None:
            return cached

        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(m.data, '$.time.created')",
        )
        query = f"""
            SELECT
                s.project_id AS project_id,
                COALESCE(p.name, p.worktree, s.project_id) AS project_name,
                p.worktree AS project_path,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT m.session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.input'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.output'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message m
            JOIN session s ON s.id = m.session_id
            LEFT JOIN project p ON p.id = s.project_id
            WHERE json_valid(m.data) = 1
              AND json_extract(m.data, '$.role') = 'assistant'
              {time_filter}
            GROUP BY s.project_id, project_name, project_path
            ORDER BY input_tokens + output_tokens + cache_read + cache_write DESC
        """

        with self._connect() as conn:
            result = conn.execute(query, params).fetchall()
            self._set_cached(cache_key, result)
            return result

    def fetch_project_usage_detail_for_day(
        self,
        *,
        day: str,
        timezone_offset_minutes: int = 0,
    ) -> list[sqlite3.Row]:
        """Fetch usage grouped by project for one local day."""
        day_filter, params = self._target_day_filter(
            day=day,
            time_expr="json_extract(m.data, '$.time.created')",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                s.project_id AS project_id,
                COALESCE(p.name, p.worktree, s.project_id) AS project_name,
                p.worktree AS project_path,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT m.session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.input'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.output'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message m
            JOIN session s ON s.id = m.session_id
            LEFT JOIN project p ON p.id = s.project_id
            WHERE json_valid(m.data) = 1
              AND json_extract(m.data, '$.role') = 'assistant'
              AND COALESCE(json_extract(m.data, '$.time.created'), 0) > 0
              {day_filter}
            GROUP BY s.project_id, project_name, project_path
            ORDER BY input_tokens + output_tokens + cache_read + cache_write DESC
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_project_model_usage(self, *, days: int | None = None) -> list[sqlite3.Row]:
        """Fetch usage grouped by project and model for cost calculation."""
        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(m.data, '$.time.created')",
        )
        query = f"""
            SELECT
                s.project_id AS project_id,
                COALESCE(
                    json_extract(m.data, '$.modelID'),
                    json_extract(m.data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(m.data, '$.providerID'),
                    json_extract(m.data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.input'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.output'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message m
            JOIN session s ON s.id = m.session_id
            WHERE json_valid(m.data) = 1
              AND json_extract(m.data, '$.role') = 'assistant'
              {time_filter}
            GROUP BY s.project_id, model_id
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_project_model_usage_for_day(
        self,
        *,
        day: str,
        timezone_offset_minutes: int = 0,
    ) -> list[sqlite3.Row]:
        """Fetch usage grouped by project and model for one local day."""
        day_filter, params = self._target_day_filter(
            day=day,
            time_expr="json_extract(m.data, '$.time.created')",
            timezone_offset_minutes=timezone_offset_minutes,
        )
        query = f"""
            SELECT
                s.project_id AS project_id,
                COALESCE(
                    json_extract(m.data, '$.modelID'),
                    json_extract(m.data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(m.data, '$.providerID'),
                    json_extract(m.data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.input'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.output'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
                , COUNT(*) AS total_interactions
            FROM message m
            JOIN session s ON s.id = m.session_id
            WHERE json_valid(m.data) = 1
              AND json_extract(m.data, '$.role') = 'assistant'
              AND COALESCE(json_extract(m.data, '$.time.created'), 0) > 0
              {day_filter}
            GROUP BY s.project_id, model_id, provider_id
        """

        with self._connect() as conn:
            return conn.execute(query, params).fetchall()

    def fetch_project_session_usage(
        self,
        *,
        project_id: str,
        days: int | None = None,
    ) -> list[sqlite3.Row]:
        """Fetch usage grouped by session for one project."""
        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(m.data, '$.time.created')",
        )
        query = f"""
            SELECT
                s.id AS session_id,
                s.title AS title,
                s.directory AS directory,
                COALESCE(s.time_updated, s.time_created, 0) AS last_updated_ms,
                COALESCE(p.name, p.worktree, s.project_id) AS project_name,
                p.worktree AS project_path,
                COUNT(*) AS total_interactions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.input'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.output'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message m
            JOIN session s ON s.id = m.session_id
            LEFT JOIN project p ON p.id = s.project_id
            WHERE json_valid(m.data) = 1
              AND json_extract(m.data, '$.role') = 'assistant'
              AND s.project_id = ?
              {time_filter}
            GROUP BY
                session_id,
                title,
                directory,
                last_updated_ms,
                project_name,
                project_path
            ORDER BY last_updated_ms DESC
        """

        with self._connect() as conn:
            return conn.execute(query, [project_id, *params]).fetchall()

    def fetch_project_session_model_usage(
        self,
        *,
        project_id: str,
        days: int | None = None,
    ) -> list[sqlite3.Row]:
        """Fetch model usage grouped by session for one project."""
        time_filter, params = self._time_filter(
            days,
            time_expr="json_extract(m.data, '$.time.created')",
        )
        query = f"""
            SELECT
                s.id AS session_id,
                COALESCE(
                    json_extract(m.data, '$.modelID'),
                    json_extract(m.data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(m.data, '$.providerID'),
                    json_extract(m.data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.input'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.output'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(m.data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(m.data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message m
            JOIN session s ON s.id = m.session_id
            WHERE json_valid(m.data) = 1
              AND json_extract(m.data, '$.role') = 'assistant'
              AND s.project_id = ?
              {time_filter}
            GROUP BY session_id, model_id
        """

        with self._connect() as conn:
            return conn.execute(query, [project_id, *params]).fetchall()

    def fetch_active_session(self) -> sqlite3.Row | None:
        """Fetch most recently updated non-archived session."""
        query = """
            SELECT
                s.id,
                s.title,
                s.directory,
                s.project_id,
                s.time_updated,
                COALESCE(p.name, p.worktree, s.project_id) AS project_name
            FROM session s
            LEFT JOIN project p ON p.id = s.project_id
            WHERE COALESCE(s.time_archived, 0) = 0
            ORDER BY s.time_updated DESC
            LIMIT 1
        """

        with self._connect() as conn:
            return conn.execute(query).fetchone()

    def fetch_live_summary_messages(self, *, since_ms: int) -> sqlite3.Row:
        """Fetch aggregate usage totals from assistant messages since timestamp."""
        query = """
            SELECT
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(json_extract(data, '$.time.created'), 0) >= ?
        """

        with self._connect() as conn:
            row = conn.execute(query, [since_ms]).fetchone()
            if row is None:
                raise RuntimeError("Live message summary query returned no row")
            return row

    def fetch_live_summary_steps(self, *, since_ms: int) -> sqlite3.Row:
        """Fetch aggregate usage totals from step-finish parts since timestamp."""
        query = """
            SELECT
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM part
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.type') = 'step-finish'
              AND COALESCE(time_created, 0) >= ?
        """

        with self._connect() as conn:
            row = conn.execute(query, [since_ms]).fetchone()
            if row is None:
                raise RuntimeError("Live step summary query returned no row")
            return row

    def fetch_live_model_usage(self, *, since_ms: int, limit: int) -> list[sqlite3.Row]:
        """Fetch model usage since timestamp."""
        query = """
            SELECT
                COALESCE(
                    json_extract(data, '$.modelID'),
                    json_extract(data, '$.model.modelID'),
                    'unknown'
                ) AS model_id,
                COALESCE(
                    json_extract(data, '$.providerID'),
                    json_extract(data, '$.model.providerID'),
                    NULL
                ) AS provider_id,
                COUNT(*) AS total_interactions,
                COUNT(DISTINCT session_id) AS total_sessions,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.input'), 0) > 0
                    THEN json_extract(data, '$.tokens.input') ELSE 0 END), 0) AS input_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.output'), 0) > 0
                    THEN json_extract(data, '$.tokens.output') ELSE 0 END), 0) AS output_tokens,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.read'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.read') ELSE 0 END), 0) AS cache_read,
                COALESCE(SUM(CASE WHEN COALESCE(json_extract(data, '$.tokens.cache.write'), 0) > 0
                    THEN json_extract(data, '$.tokens.cache.write') ELSE 0 END), 0) AS cache_write
            FROM message
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.role') = 'assistant'
              AND COALESCE(json_extract(data, '$.time.created'), 0) >= ?
            GROUP BY model_id, provider_id
            ORDER BY input_tokens + output_tokens + cache_read + cache_write DESC
            LIMIT ?
        """

        with self._connect() as conn:
            return conn.execute(query, [since_ms, limit]).fetchall()

    def fetch_live_tool_usage(self, *, since_ms: int, limit: int) -> list[sqlite3.Row]:
        """Fetch tool usage since timestamp from tool parts."""
        query = """
            SELECT
                COALESCE(json_extract(data, '$.tool'), 'unknown') AS tool_name,
                COUNT(*) AS total_calls
            FROM part
            WHERE json_valid(data) = 1
              AND json_extract(data, '$.type') = 'tool'
              AND COALESCE(time_created, 0) >= ?
            GROUP BY tool_name
            ORDER BY total_calls DESC
            LIMIT ?
        """

        with self._connect() as conn:
            return conn.execute(query, [since_ms, limit]).fetchall()
