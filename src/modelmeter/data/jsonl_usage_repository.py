"""JSONL data reader for Claude Code usage tracking."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Literal

from modelmeter.core.providers import provider_from_model_id

RowDict = dict[str, Any]


@dataclass
class Interaction:
    model_id: str
    provider_id: str | None
    input_tokens: int
    output_tokens: int
    cache_read: int
    cache_write: int
    timestamp_ms: int
    session_id: str


@dataclass
class SessionData:
    session_id: str
    title: str | None
    project_id: str
    project_name: str
    project_path: str
    cwd: str
    time_created_ms: int
    time_updated_ms: int
    interactions: list[Interaction]
    model_count: int
    message_count: int


@dataclass
class SessionIndex:
    sessions: list[SessionData]
    project_map: dict[str, dict[str, Any]]
    session_mtime_map: dict[str, int]
    sessions_by_id: dict[str, SessionData]


class JsonlUsageRepository:
    """Repository for reading Claude Code JSONL usage data."""

    def __init__(self, data_dir: Path) -> None:
        self._data_dir = data_dir
        self._cached_index: SessionIndex | None = None
        self._cached_mtimes: dict[Path, float] = {}

    def get_index(self) -> SessionIndex:
        """Public accessor for the session index."""
        return self._ensure_index()

    def _ensure_index(self) -> SessionIndex:
        """Rebuild index if files changed, otherwise return cached."""
        current_mtimes = self._scan_file_mtimes()
        if self._cached_index is not None and current_mtimes == self._cached_mtimes:
            return self._cached_index

        self._cached_index = self._build_index()
        self._cached_mtimes = current_mtimes
        return self._cached_index

    def _scan_file_mtimes(self) -> dict[Path, float]:
        """Scan all relevant JSONL files and their modification times."""
        mtimes: dict[Path, float] = {}
        if not self._data_dir.exists():
            return mtimes

        for jsonl_file in self._data_dir.rglob("*.jsonl"):
            mtimes[jsonl_file] = jsonl_file.stat().st_mtime
        return mtimes

    def _scan_jsonl_files(self) -> list[tuple[Path, list[Path]]]:
        """
        Find all session JSONL files grouped by project directory.

        Returns list of (project_dir, list of session files) tuples.
        """
        if not self._data_dir.exists():
            return []

        projects: dict[Path, list[Path]] = {}
        for jsonl_file in self._data_dir.rglob("*.jsonl"):
            # Skip any subagent data entirely; only group top-level session files.
            if "subagents" in jsonl_file.parts:
                continue

            project_dir = jsonl_file.parent

            if project_dir not in projects:
                projects[project_dir] = []

            projects[project_dir].append(jsonl_file)

        return [(p, files) for p, files in projects.items()]

    def _session_file_mtime_ms(self, session_id: str) -> int | None:
        """Return effective mtime for a session (max of parent + subagent files).

        Uses the precomputed map from the session index to avoid per-call directory scans.
        """
        index = self._ensure_index()
        return index.session_mtime_map.get(session_id)

    def _parse_session_file(self, path: Path) -> list[dict[str, Any]]:
        """Parse a single JSONL file into a list of records."""
        records: list[dict[str, Any]] = []
        if not path.exists():
            return records

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        records.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
        return records

    def _load_subagent_records(self, session_dir: Path, session_id: str) -> list[dict[str, Any]]:
        """Load subagent records for a given session."""
        subagent_dir = session_dir / "subagents"
        if not subagent_dir.exists():
            return []

        records: list[dict[str, Any]] = []
        for subagent_file in subagent_dir.glob("*.jsonl"):
            records.extend(self._parse_session_file(subagent_file))
        return records

    def _load_subagent_records_from_dir(self, subagent_dir: Path) -> list[dict[str, Any]]:
        """Load subagent records from a specific directory."""
        if not subagent_dir.exists():
            return []

        records: list[dict[str, Any]] = []
        for subagent_file in subagent_dir.glob("*.jsonl"):
            records.extend(self._parse_session_file(subagent_file))
        return records

    def _build_session_from_records(
        self,
        records: list[dict[str, Any]],
        subagent_records: list[dict[str, Any]],
    ) -> SessionData | None:
        """Build SessionData from parsed records."""
        if not records:
            return None

        first_record = records[0]
        cwd = first_record.get("cwd", "")
        session_id = first_record.get("sessionId", "")

        if not cwd or not session_id:
            return None

        project_path = cwd
        project_id = hashlib.md5(cwd.encode()).hexdigest()[:16]
        project_name = Path(cwd).name

        title: str | None = None
        for rec in records:
            rec_type = rec.get("type", "")
            if rec_type == "custom-title":
                title = rec.get("title")
                break

        time_created_ms = 0
        time_updated_ms = 0
        for rec in records:
            ts = rec.get("timestamp")
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    ts_ms = int(dt.timestamp() * 1000)
                    if time_created_ms == 0 or ts_ms < time_created_ms:
                        time_created_ms = ts_ms
                    if ts_ms > time_updated_ms:
                        time_updated_ms = ts_ms
                except (ValueError, OSError):
                    pass

        all_records = records + subagent_records

        interactions: list[Interaction] = []
        model_ids: set[str] = set()

        for rec in all_records:
            rec_type = rec.get("type", "")
            if rec_type != "assistant":
                continue

            # Claude Code nests model/usage/stop_reason inside message;
            # fall back to top-level for older formats.
            msg = rec.get("message", {})
            model_id = msg.get("model") or rec.get("model", "unknown")
            usage = msg.get("usage") or rec.get("usage", {})

            input_tokens = usage.get("input_tokens", 0)
            output_tokens = usage.get("output_tokens", 0)
            if input_tokens == 0 and output_tokens == 0:
                continue

            ts = rec.get("timestamp", "")

            timestamp_ms = 0
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamp_ms = int(dt.timestamp() * 1000)
                except (ValueError, OSError):
                    pass

            provider_id = provider_from_model_id(model_id)

            cache_read = usage.get("cache_read_input_tokens") or usage.get("cache_read", 0)
            cache_write = usage.get("cache_creation_input_tokens") or usage.get("cache_write", 0)

            interaction = Interaction(
                model_id=model_id,
                provider_id=provider_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                cache_read=cache_read,
                cache_write=cache_write,
                timestamp_ms=timestamp_ms,
                session_id=session_id,
            )
            interactions.append(interaction)
            model_ids.add(model_id)

        return SessionData(
            session_id=session_id,
            title=title,
            project_id=project_id,
            project_name=project_name,
            project_path=project_path,
            cwd=cwd,
            time_created_ms=time_created_ms,
            time_updated_ms=time_updated_ms,
            interactions=interactions,
            model_count=len(model_ids),
            message_count=len([r for r in all_records if r.get("type") in ("user", "assistant")]),
        )

    def _build_index(self) -> SessionIndex:
        """Build the complete session index from all JSONL files."""
        sessions: list[SessionData] = []
        project_map: dict[str, dict[str, Any]] = {}
        session_mtime_map: dict[str, int] = {}

        project_groups = self._scan_jsonl_files()

        for project_dir, session_files in project_groups:
            # Normalize dash-encoded directory name to an absolute path.
            # Claude Code encodes e.g. /Users/alice/src as -Users-alice-src.
            # Replace dashes with slashes, then ensure exactly one leading slash.
            cwd = "/" + project_dir.name.replace("-", "/").lstrip("/")

            project_id = hashlib.md5(cwd.encode()).hexdigest()[:16]
            project_name = Path(cwd).name if cwd else "unknown"

            project_map[project_id] = {
                "project_id": project_id,
                "project_name": project_name,
                "project_path": cwd,
            }

            for session_file in session_files:
                session_dir = session_file.parent
                session_stem = session_file.stem
                records = self._parse_session_file(session_file)

                session_id = session_stem
                if records:
                    session_id = records[0].get("sessionId", session_id)

                subagent_dir = session_dir / session_stem / "subagents"
                subagent_records = self._load_subagent_records_from_dir(subagent_dir)

                # Precompute effective mtime: max of session file and any subagent files.
                try:
                    effective_mtime = int(session_file.stat().st_mtime * 1000)
                except OSError:
                    effective_mtime = 0
                if subagent_dir.exists():
                    for sub in subagent_dir.glob("*.jsonl"):
                        try:
                            sub_mtime = int(sub.stat().st_mtime * 1000)
                        except OSError:
                            continue
                        if sub_mtime > effective_mtime:
                            effective_mtime = sub_mtime
                session_mtime_map[session_id] = effective_mtime

                session_data = self._build_session_from_records(records, subagent_records)
                if session_data:
                    sessions.append(session_data)

        sessions.sort(key=lambda s: s.time_created_ms)
        sessions_by_id = {s.session_id: s for s in sessions}

        return SessionIndex(
            sessions=sessions,
            project_map=project_map,
            session_mtime_map=session_mtime_map,
            sessions_by_id=sessions_by_id,
        )

    def _filter_interactions(self, days: int | None) -> list[tuple[SessionData, Interaction]]:
        """Filter interactions by days cutoff, return (session, interaction) pairs."""
        index = self._ensure_index()
        if days is None:
            return [(s, i) for s in index.sessions for i in s.interactions]

        cutoff_ms = int((datetime.now(tz=UTC) - timedelta(days=days)).timestamp() * 1000)
        return [
            (s, i) for s in index.sessions for i in s.interactions if i.timestamp_ms >= cutoff_ms
        ]

    def _filter_interactions_for_day(
        self,
        day: str,
        timezone_offset_minutes: int = 0,
    ) -> list[tuple[SessionData, Interaction]]:
        """Filter interactions to a specific local day."""
        index = self._ensure_index()

        try:
            day_dt = datetime.fromisoformat(day).date()
        except ValueError:
            return []

        tz = timezone(timedelta(minutes=timezone_offset_minutes))
        day_start = int(
            datetime(1970, 1, 1, tzinfo=tz)
            .replace(year=day_dt.year, month=day_dt.month, day=day_dt.day)
            .timestamp()
            * 1000
        )
        next_day = day_dt + timedelta(days=1)
        day_end_exclusive = int(
            datetime(1970, 1, 1, tzinfo=tz)
            .replace(year=next_day.year, month=next_day.month, day=next_day.day)
            .timestamp()
            * 1000
        )

        return [
            (s, i)
            for s in index.sessions
            for i in s.interactions
            if day_start <= i.timestamp_ms < day_end_exclusive
        ]

    def fetch_summary(self, *, days: int | None = None) -> RowDict:
        """Fetch aggregate usage totals and distinct session count."""
        pairs = self._filter_interactions(days)

        input_tokens = sum(i.input_tokens for _, i in pairs)
        output_tokens = sum(i.output_tokens for _, i in pairs)
        cache_read = sum(i.cache_read for _, i in pairs)
        cache_write = sum(i.cache_write for _, i in pairs)
        total_sessions = len(set(s.session_id for s, _ in pairs))

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "total_sessions": total_sessions,
        }

    def fetch_summary_steps(self, *, days: int | None = None) -> RowDict:
        """For JSONL, equivalent to fetch_summary (no step-finish concept)."""
        return self.fetch_summary(days=days)

    def fetch_summary_for_day(self, *, day: str, timezone_offset_minutes: int = 0) -> RowDict:
        """Fetch aggregate usage totals for one local day."""
        pairs = self._filter_interactions_for_day(day, timezone_offset_minutes)

        input_tokens = sum(i.input_tokens for _, i in pairs)
        output_tokens = sum(i.output_tokens for _, i in pairs)
        cache_read = sum(i.cache_read for _, i in pairs)
        cache_write = sum(i.cache_write for _, i in pairs)
        total_sessions = len(set(s.session_id for s, _ in pairs))
        total_interactions = len(pairs)

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "total_sessions": total_sessions,
            "total_interactions": total_interactions,
        }

    def fetch_summary_for_day_steps(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> RowDict | None:
        """For JSONL, equivalent to fetch_summary_for_day."""
        return self.fetch_summary_for_day(day=day, timezone_offset_minutes=timezone_offset_minutes)

    def fetch_session_count(self, *, days: int | None = None) -> int:
        """Count distinct session IDs within time window."""
        index = self._ensure_index()
        if days is None:
            return len(set(s.session_id for s in index.sessions))

        cutoff_ms = int((datetime.now(tz=UTC) - timedelta(days=days)).timestamp() * 1000)
        return len(
            set(
                s.session_id
                for s in index.sessions
                if any(i.timestamp_ms >= cutoff_ms for i in s.interactions)
            )
        )

    def fetch_daily(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """Group interactions by day, return list of dicts."""
        self._ensure_index()
        pairs = self._filter_interactions(days)

        tz = timezone(timedelta(minutes=timezone_offset_minutes))
        daily_data: dict[str, dict[str, Any]] = {}

        for session, interaction in pairs:
            day_ts = datetime.fromtimestamp(interaction.timestamp_ms / 1000, tz=tz)
            day_str = day_ts.strftime("%Y-%m-%d")

            if day_str not in daily_data:
                daily_data[day_str] = {
                    "day": day_str,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                    "total_sessions": set(),
                }

            daily_data[day_str]["input_tokens"] += interaction.input_tokens
            daily_data[day_str]["output_tokens"] += interaction.output_tokens
            daily_data[day_str]["cache_read"] += interaction.cache_read
            daily_data[day_str]["cache_write"] += interaction.cache_write
            daily_data[day_str]["total_sessions"].add(session.session_id)

        result: list[RowDict] = []
        for day_str in sorted(daily_data.keys()):
            data = daily_data[day_str]
            result.append(
                {
                    "day": data["day"],
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cache_read": data["cache_read"],
                    "cache_write": data["cache_write"],
                    "total_sessions": len(data["total_sessions"]),
                }
            )

        return result

    def fetch_daily_steps(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """For JSONL, equivalent to fetch_daily."""
        return self.fetch_daily(days=days, timezone_offset_minutes=timezone_offset_minutes)

    def fetch_daily_session_counts(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> dict[str, int]:
        """Sessions per day."""
        rows = self.fetch_daily(days=days, timezone_offset_minutes=timezone_offset_minutes)
        return {row["day"]: row["total_sessions"] for row in rows}

    def resolve_token_source(
        self,
        *,
        days: int | None,
        token_source: Literal["auto", "message", "steps"],
    ) -> Literal["message", "steps"]:
        """Always return 'message' for JSONL (no step-finish concept)."""
        if token_source != "auto":
            return token_source
        return "message"

    def resolve_session_count_source(
        self,
        *,
        days: int | None,
        session_count_source: Literal["auto", "activity", "session"],
    ) -> Literal["activity", "session"]:
        """Always return 'activity' for JSONL."""
        if session_count_source != "auto":
            return session_count_source
        return "activity"

    def fetch_model_usage(self, *, days: int | None = None) -> list[RowDict]:
        """Group by model_id, aggregate tokens."""
        pairs = self._filter_interactions(days)

        model_data: dict[str, dict[str, Any]] = {}
        for _, interaction in pairs:
            model_id = interaction.model_id
            if model_id not in model_data:
                model_data[model_id] = {
                    "model_id": model_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            model_data[model_id]["input_tokens"] += interaction.input_tokens
            model_data[model_id]["output_tokens"] += interaction.output_tokens
            model_data[model_id]["cache_read"] += interaction.cache_read
            model_data[model_id]["cache_write"] += interaction.cache_write

        return list(model_data.values())

    def fetch_model_usage_detail(self, *, days: int | None = None) -> list[RowDict]:
        """Group by (model_id, provider_id), include counts."""
        pairs = self._filter_interactions(days)

        model_data: dict[tuple[str, str | None], dict[str, Any]] = {}
        for _, interaction in pairs:
            key = (interaction.model_id, interaction.provider_id)
            if key not in model_data:
                model_data[key] = {
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "total_interactions": 0,
                    "total_sessions": set(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            model_data[key]["total_interactions"] += 1
            model_data[key]["total_sessions"].add(interaction.session_id)
            model_data[key]["input_tokens"] += interaction.input_tokens
            model_data[key]["output_tokens"] += interaction.output_tokens
            model_data[key]["cache_read"] += interaction.cache_read
            model_data[key]["cache_write"] += interaction.cache_write

        result: list[RowDict] = []
        for _, data in model_data.items():
            result.append(
                {
                    "model_id": data["model_id"],
                    "provider_id": data["provider_id"],
                    "total_interactions": data["total_interactions"],
                    "total_sessions": len(data["total_sessions"]),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cache_read": data["cache_read"],
                    "cache_write": data["cache_write"],
                }
            )

        result.sort(
            key=lambda r: (
                r["input_tokens"] + r["output_tokens"] + r["cache_read"] + r["cache_write"]
            ),
            reverse=True,
        )
        return result

    def fetch_model_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """Same as fetch_model_usage_detail for single day."""
        pairs = self._filter_interactions_for_day(day, timezone_offset_minutes)

        model_data: dict[tuple[str, str | None], dict[str, Any]] = {}
        for session, interaction in pairs:
            key = (interaction.model_id, interaction.provider_id)
            if key not in model_data:
                model_data[key] = {
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "total_interactions": 0,
                    "total_sessions": set(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            model_data[key]["total_interactions"] += 1
            model_data[key]["total_sessions"].add(session.session_id)
            model_data[key]["input_tokens"] += interaction.input_tokens
            model_data[key]["output_tokens"] += interaction.output_tokens
            model_data[key]["cache_read"] += interaction.cache_read
            model_data[key]["cache_write"] += interaction.cache_write

        result: list[RowDict] = []
        for _, data in model_data.items():
            result.append(
                {
                    "model_id": data["model_id"],
                    "provider_id": data["provider_id"],
                    "total_interactions": data["total_interactions"],
                    "total_sessions": len(data["total_sessions"]),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cache_read": data["cache_read"],
                    "cache_write": data["cache_write"],
                }
            )

        result.sort(
            key=lambda r: (
                r["input_tokens"] + r["output_tokens"] + r["cache_read"] + r["cache_write"]
            ),
            reverse=True,
        )
        return result

    def fetch_model_detail(self, *, model_id: str, days: int | None = None) -> RowDict | None:
        """Aggregate for specific model."""
        pairs = self._filter_interactions(days)

        input_tokens = 0
        output_tokens = 0
        cache_read = 0
        cache_write = 0
        total_interactions = 0
        sessions: set[str] = set()

        for _, interaction in pairs:
            if interaction.model_id == model_id:
                total_interactions += 1
                sessions.add(interaction.session_id)
                input_tokens += interaction.input_tokens
                output_tokens += interaction.output_tokens
                cache_read += interaction.cache_read
                cache_write += interaction.cache_write

        if total_interactions == 0:
            return None

        return {
            "provider_id": next(
                (i.provider_id for _, i in pairs if i.model_id == model_id and i.provider_id), None
            ),
            "total_interactions": total_interactions,
            "total_sessions": len(sessions),
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
        }

    def fetch_daily_model_detail(self, *, model_id: str, days: int | None = None) -> list[RowDict]:
        """Daily breakdown for one model."""
        pairs = self._filter_interactions(days)

        tz = UTC
        daily_data: dict[str, dict[str, Any]] = {}

        for session, interaction in pairs:
            if interaction.model_id != model_id:
                continue

            day_ts = datetime.fromtimestamp(interaction.timestamp_ms / 1000, tz=tz)
            day_str = day_ts.strftime("%Y-%m-%d")

            if day_str not in daily_data:
                daily_data[day_str] = {
                    "day": day_str,
                    "total_interactions": 0,
                    "total_sessions": set(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            daily_data[day_str]["total_interactions"] += 1
            daily_data[day_str]["total_sessions"].add(session.session_id)
            daily_data[day_str]["input_tokens"] += interaction.input_tokens
            daily_data[day_str]["output_tokens"] += interaction.output_tokens
            daily_data[day_str]["cache_read"] += interaction.cache_read
            daily_data[day_str]["cache_write"] += interaction.cache_write

        result: list[RowDict] = []
        for day_str in sorted(daily_data.keys()):
            data = daily_data[day_str]
            result.append(
                {
                    "day": data["day"],
                    "total_interactions": data["total_interactions"],
                    "total_sessions": len(data["total_sessions"]),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cache_read": data["cache_read"],
                    "cache_write": data["cache_write"],
                }
            )

        return result

    def fetch_daily_model_usage(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """Group by (day, model_id, provider_id)."""
        pairs = self._filter_interactions(days)

        tz = timezone(timedelta(minutes=timezone_offset_minutes))
        daily_data: dict[tuple[str, str, str | None], dict[str, Any]] = {}

        for _, interaction in pairs:
            day_ts = datetime.fromtimestamp(interaction.timestamp_ms / 1000, tz=tz)
            day_str = day_ts.strftime("%Y-%m-%d")
            key = (day_str, interaction.model_id, interaction.provider_id)

            if key not in daily_data:
                daily_data[key] = {
                    "day": day_str,
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            daily_data[key]["input_tokens"] += interaction.input_tokens
            daily_data[key]["output_tokens"] += interaction.output_tokens
            daily_data[key]["cache_read"] += interaction.cache_read
            daily_data[key]["cache_write"] += interaction.cache_write

        result = [data for data in daily_data.values()]
        result.sort(key=lambda r: (r["day"], r["model_id"]))
        return result

    def fetch_project_usage_detail(self, *, days: int | None = None) -> list[RowDict]:
        """Group by project, aggregate tokens and counts."""
        pairs = self._filter_interactions(days)

        project_data: dict[str, dict[str, Any]] = {}
        for session, interaction in pairs:
            project_id = session.project_id
            if project_id not in project_data:
                project_data[project_id] = {
                    "project_id": project_id,
                    "project_name": session.project_name,
                    "project_path": session.project_path,
                    "total_interactions": 0,
                    "total_sessions": set(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            project_data[project_id]["total_interactions"] += 1
            project_data[project_id]["total_sessions"].add(session.session_id)
            project_data[project_id]["input_tokens"] += interaction.input_tokens
            project_data[project_id]["output_tokens"] += interaction.output_tokens
            project_data[project_id]["cache_read"] += interaction.cache_read
            project_data[project_id]["cache_write"] += interaction.cache_write

        result: list[RowDict] = []
        for _, data in project_data.items():
            result.append(
                {
                    "project_id": data["project_id"],
                    "project_name": data["project_name"],
                    "project_path": data["project_path"],
                    "total_interactions": data["total_interactions"],
                    "total_sessions": len(data["total_sessions"]),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cache_read": data["cache_read"],
                    "cache_write": data["cache_write"],
                }
            )

        result.sort(
            key=lambda r: (
                r["input_tokens"] + r["output_tokens"] + r["cache_read"] + r["cache_write"]
            ),
            reverse=True,
        )
        return result

    def fetch_project_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """Same as fetch_project_usage_detail for single day."""
        pairs = self._filter_interactions_for_day(day, timezone_offset_minutes)

        project_data: dict[str, dict[str, Any]] = {}
        for session, interaction in pairs:
            project_id = session.project_id
            if project_id not in project_data:
                project_data[project_id] = {
                    "project_id": project_id,
                    "project_name": session.project_name,
                    "project_path": session.project_path,
                    "total_interactions": 0,
                    "total_sessions": set(),
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            project_data[project_id]["total_interactions"] += 1
            project_data[project_id]["total_sessions"].add(session.session_id)
            project_data[project_id]["input_tokens"] += interaction.input_tokens
            project_data[project_id]["output_tokens"] += interaction.output_tokens
            project_data[project_id]["cache_read"] += interaction.cache_read
            project_data[project_id]["cache_write"] += interaction.cache_write

        result: list[RowDict] = []
        for _, data in project_data.items():
            result.append(
                {
                    "project_id": data["project_id"],
                    "project_name": data["project_name"],
                    "project_path": data["project_path"],
                    "total_interactions": data["total_interactions"],
                    "total_sessions": len(data["total_sessions"]),
                    "input_tokens": data["input_tokens"],
                    "output_tokens": data["output_tokens"],
                    "cache_read": data["cache_read"],
                    "cache_write": data["cache_write"],
                }
            )

        result.sort(
            key=lambda r: (
                r["input_tokens"] + r["output_tokens"] + r["cache_read"] + r["cache_write"]
            ),
            reverse=True,
        )
        return result

    def fetch_project_model_usage(self, *, days: int | None = None) -> list[RowDict]:
        """Group by (project_id, model_id)."""
        pairs = self._filter_interactions(days)

        project_model_data: dict[tuple[str, str], dict[str, Any]] = {}
        for session, interaction in pairs:
            key = (session.project_id, interaction.model_id)
            if key not in project_model_data:
                project_model_data[key] = {
                    "project_id": session.project_id,
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            project_model_data[key]["input_tokens"] += interaction.input_tokens
            project_model_data[key]["output_tokens"] += interaction.output_tokens
            project_model_data[key]["cache_read"] += interaction.cache_read
            project_model_data[key]["cache_write"] += interaction.cache_write

        return list(project_model_data.values())

    def fetch_project_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """Same as fetch_project_model_usage for single day."""
        pairs = self._filter_interactions_for_day(day, timezone_offset_minutes)

        project_model_data: dict[tuple[str, str, str | None], dict[str, Any]] = {}
        for session, interaction in pairs:
            key = (session.project_id, interaction.model_id, interaction.provider_id)
            if key not in project_model_data:
                project_model_data[key] = {
                    "project_id": session.project_id,
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                    "total_interactions": 0,
                }

            project_model_data[key]["input_tokens"] += interaction.input_tokens
            project_model_data[key]["output_tokens"] += interaction.output_tokens
            project_model_data[key]["cache_read"] += interaction.cache_read
            project_model_data[key]["cache_write"] += interaction.cache_write
            project_model_data[key]["total_interactions"] += 1

        return list(project_model_data.values())

    def fetch_session_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[RowDict]:
        """Group by (session_id, model_id) for one local day."""
        pairs = self._filter_interactions_for_day(day, timezone_offset_minutes)

        session_model_data: dict[tuple[str, str], dict[str, Any]] = {}
        for session, interaction in pairs:
            key = (session.session_id, interaction.model_id)
            if key not in session_model_data:
                session_model_data[key] = {
                    "session_id": session.session_id,
                    "session_title": session.title,
                    "project_id": session.project_id,
                    "project_name": session.project_name,
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                    "total_interactions": 0,
                    "started_at_ms": interaction.timestamp_ms,
                }

            session_model_data[key]["input_tokens"] += interaction.input_tokens
            session_model_data[key]["output_tokens"] += interaction.output_tokens
            session_model_data[key]["cache_read"] += interaction.cache_read
            session_model_data[key]["cache_write"] += interaction.cache_write
            session_model_data[key]["total_interactions"] += 1
            if interaction.timestamp_ms < session_model_data[key]["started_at_ms"]:
                session_model_data[key]["started_at_ms"] = interaction.timestamp_ms

        result = list(session_model_data.values())
        result.sort(
            key=lambda r: (
                r["input_tokens"] + r["output_tokens"] + r["cache_read"] + r["cache_write"]
            ),
            reverse=True,
        )
        return result

    def fetch_project_session_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[RowDict]:
        """Sessions for one project."""
        self._ensure_index()
        pairs = self._filter_interactions(days)

        session_data: dict[str, dict[str, Any]] = {}
        for session, interaction in pairs:
            if session.project_id != project_id:
                continue

            if session.session_id not in session_data:
                session_data[session.session_id] = {
                    "session_id": session.session_id,
                    "title": session.title,
                    "directory": session.project_path,
                    "last_updated_ms": session.time_updated_ms,
                    "project_name": session.project_name,
                    "project_path": session.project_path,
                    "total_interactions": 0,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            session_data[session.session_id]["total_interactions"] += 1
            session_data[session.session_id]["input_tokens"] += interaction.input_tokens
            session_data[session.session_id]["output_tokens"] += interaction.output_tokens
            session_data[session.session_id]["cache_read"] += interaction.cache_read
            session_data[session.session_id]["cache_write"] += interaction.cache_write
            if interaction.timestamp_ms > session_data[session.session_id]["last_updated_ms"]:
                session_data[session.session_id]["last_updated_ms"] = interaction.timestamp_ms

        result = list(session_data.values())
        result.sort(key=lambda r: r["last_updated_ms"], reverse=True)
        return result

    def fetch_project_session_model_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[RowDict]:
        """Model usage by session for one project."""
        pairs = self._filter_interactions(days)

        session_model_data: dict[tuple[str, str], dict[str, Any]] = {}
        for session, interaction in pairs:
            if session.project_id != project_id:
                continue

            key = (session.session_id, interaction.model_id)
            if key not in session_model_data:
                session_model_data[key] = {
                    "session_id": session.session_id,
                    "model_id": interaction.model_id,
                    "provider_id": interaction.provider_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                }

            session_model_data[key]["input_tokens"] += interaction.input_tokens
            session_model_data[key]["output_tokens"] += interaction.output_tokens
            session_model_data[key]["cache_read"] += interaction.cache_read
            session_model_data[key]["cache_write"] += interaction.cache_write

        return list(session_model_data.values())

    def get_session_row(self, session_id: str) -> RowDict | None:
        """Get a single session by ID as a RowDict, using O(1) index lookup."""
        index = self._ensure_index()
        s = index.sessions_by_id.get(session_id)
        if s is None:
            return None
        mtime_ms = index.session_mtime_map.get(session_id) or s.time_updated_ms
        return {
            "id": s.session_id,
            "title": s.title,
            "directory": s.project_path,
            "project_id": s.project_id,
            "time_updated": mtime_ms,
            "project_name": s.project_name,
        }

    def fetch_active_session(self, *, session_id: str | None = None) -> RowDict | None:
        """Get most recent active session."""
        index = self._ensure_index()

        def sort_key(session: SessionData) -> int:
            return self._session_file_mtime_ms(session.session_id) or session.time_updated_ms

        sessions = sorted(index.sessions, key=sort_key, reverse=True)

        if session_id:
            for s in sessions:
                mtime_ms = self._session_file_mtime_ms(s.session_id) or s.time_updated_ms
                if s.session_id == session_id:
                    return {
                        "id": s.session_id,
                        "title": s.title,
                        "directory": s.project_path,
                        "project_id": s.project_id,
                        "time_updated": mtime_ms,
                        "project_name": s.project_name,
                    }
            return None

        return (
            {
                "id": sessions[0].session_id,
                "title": sessions[0].title,
                "directory": sessions[0].project_path,
                "project_id": sessions[0].project_id,
                "time_updated": self._session_file_mtime_ms(sessions[0].session_id)
                or sessions[0].time_updated_ms,
                "project_name": sessions[0].project_name,
            }
            if sessions
            else None
        )

    def fetch_sessions_summary(
        self,
        *,
        limit: int = 20,
        include_archived: bool = False,
        min_time_updated_ms: int | None = None,
    ) -> list[RowDict]:
        """Recent sessions with metadata."""
        index = self._ensure_index()

        def effective_time_updated_ms(session: SessionData) -> int:
            return self._session_file_mtime_ms(session.session_id) or session.time_updated_ms

        sessions = sorted(index.sessions, key=effective_time_updated_ms, reverse=True)

        if min_time_updated_ms is not None:
            sessions = [s for s in sessions if effective_time_updated_ms(s) >= min_time_updated_ms]

        sessions = sessions[:limit]

        result: list[RowDict] = []
        for s in sessions:
            time_updated_ms = effective_time_updated_ms(s)
            result.append(
                {
                    "session_id": s.session_id,
                    "title": s.title,
                    "directory": s.project_path,
                    "time_created": s.time_created_ms,
                    "time_updated": time_updated_ms,
                    "time_archived": None,
                    "project_name": s.project_name,
                    "project_id": s.project_id,
                    "message_count": s.message_count,
                    "model_count": s.model_count,
                    "token_count": sum(i.input_tokens + i.output_tokens for i in s.interactions),
                }
            )

        return result

    def fetch_live_summary_messages(
        self, *, since_ms: int, session_id: str | None = None
    ) -> RowDict:
        """Aggregate since timestamp."""
        index = self._ensure_index()
        pairs = [
            (s, i) for s in index.sessions for i in s.interactions if i.timestamp_ms >= since_ms
        ]

        if session_id:
            pairs = [(s, i) for s, i in pairs if s.session_id == session_id]

        input_tokens = sum(i.input_tokens for _, i in pairs)
        output_tokens = sum(i.output_tokens for _, i in pairs)
        cache_read = sum(i.cache_read for _, i in pairs)
        cache_write = sum(i.cache_write for _, i in pairs)
        total_sessions = len(set(s.session_id for s, _ in pairs))

        return {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "total_sessions": total_sessions,
            "total_interactions": len(pairs),
        }

    def fetch_live_summary_steps(self, *, since_ms: int, session_id: str | None = None) -> RowDict:
        """Same as fetch_live_summary_messages for JSONL."""
        return self.fetch_live_summary_messages(since_ms=since_ms, session_id=session_id)

    def fetch_live_model_usage(
        self, *, since_ms: int, limit: int = 5, session_id: str | None = None
    ) -> list[RowDict]:
        """Model usage since timestamp."""
        index = self._ensure_index()
        pairs = [
            (s, i) for s in index.sessions for i in s.interactions if i.timestamp_ms >= since_ms
        ]

        if session_id:
            pairs = [(s, i) for s, i in pairs if s.session_id == session_id]

        model_data: dict[str, dict[str, Any]] = {}
        for _, interaction in pairs:
            model_id = interaction.model_id
            if model_id not in model_data:
                model_data[model_id] = {
                    "model_id": model_id,
                    "input_tokens": 0,
                    "output_tokens": 0,
                    "cache_read": 0,
                    "cache_write": 0,
                    "sessions": set(),
                    "total_interactions": 0,
                }

            model_data[model_id]["input_tokens"] += interaction.input_tokens
            model_data[model_id]["output_tokens"] += interaction.output_tokens
            model_data[model_id]["cache_read"] += interaction.cache_read
            model_data[model_id]["cache_write"] += interaction.cache_write
            model_data[model_id]["sessions"].add(interaction.session_id)
            model_data[model_id]["total_interactions"] += 1

        result: list[RowDict] = []
        for row in model_data.values():
            sessions = row.pop("sessions")
            row["total_sessions"] = len(sessions)
            result.append(row)
        result.sort(key=lambda r: r["input_tokens"] + r["output_tokens"], reverse=True)
        return result[:limit]

    def fetch_live_tool_usage(
        self, *, since_ms: int, limit: int = 8, session_id: str | None = None
    ) -> list[RowDict]:
        """Tool usage since timestamp - stub for JSONL (no tool data)."""
        return []
