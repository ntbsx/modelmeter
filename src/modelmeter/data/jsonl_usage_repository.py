"""JSONL data reader for Claude Code usage tracking."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

from modelmeter.core.providers import provider_from_model_id


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
            if jsonl_file.name == "subagents":
                continue

            project_dir = jsonl_file.parent
            if project_dir.name == "subagents":
                project_dir = project_dir.parent

            if project_dir not in projects:
                projects[project_dir] = []

            if "subagents" not in jsonl_file.parts:
                projects[project_dir].append(jsonl_file)

        return [(p, files) for p, files in projects.items()]

    def _parse_session_file(self, path: Path) -> list[dict[str, Any]]:
        """Parse a single JSONL file into a list of records."""
        records: list[dict[str, Any]] = []
        if not path.exists():
            return records

        with open(path, "r", encoding="utf-8") as f:
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

            stop_reason = rec.get("stop_reason")
            if stop_reason is None:
                continue

            model_id = rec.get("model", "unknown")
            usage = rec.get("usage", {})
            ts = rec.get("timestamp", "")

            timestamp_ms = 0
            if ts:
                try:
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    timestamp_ms = int(dt.timestamp() * 1000)
                except (ValueError, OSError):
                    pass

            provider_id = provider_from_model_id(model_id)

            interaction = Interaction(
                model_id=model_id,
                provider_id=provider_id,
                input_tokens=usage.get("input_tokens", 0),
                output_tokens=usage.get("output_tokens", 0),
                cache_read=usage.get("cache_read", 0),
                cache_write=usage.get("cache_write", 0),
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

        project_groups = self._scan_jsonl_files()

        for project_dir, session_files in project_groups:
            cwd = project_dir.name.replace("-", "/")
            if cwd.startswith("/"):
                parts = cwd.split("/")
                if len(parts) >= 3:
                    cwd = "/".join(parts[1:])
                else:
                    cwd = "/" + "/".join(parts[1:])
            else:
                cwd = "/" + cwd

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

                session_data = self._build_session_from_records(records, subagent_records)
                if session_data:
                    sessions.append(session_data)

        sessions.sort(key=lambda s: s.time_created_ms)

        return SessionIndex(sessions=sessions, project_map=project_map)
