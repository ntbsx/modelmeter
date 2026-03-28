"""Storage path discovery for agent data sources."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from modelmeter.config.settings import AppSettings


@dataclass(frozen=True)
class StoragePaths:
    """Resolved paths to agent data sources."""

    data_dir: Path
    sqlite_db_path: Path
    legacy_message_dirs: tuple[Path, ...]


def resolve_storage_paths(
    settings: AppSettings, db_path_override: Path | None = None
) -> StoragePaths:
    """Resolve SQLite and legacy message storage paths."""
    data_dir = settings.opencode_data_dir
    configured_db_path = db_path_override or settings.opencode_db_path
    sqlite_db_path = configured_db_path if configured_db_path else data_dir / "opencode.db"

    candidates: list[Path] = [
        data_dir / "storage" / "message",
    ]

    project_root = data_dir / "project"
    if project_root.exists():
        for project_dir in project_root.iterdir():
            storage_dir = project_dir / "storage" / "message"
            if storage_dir.exists():
                candidates.append(storage_dir)

    unique_candidates: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        key = str(candidate)
        if key in seen:
            continue
        seen.add(key)
        unique_candidates.append(candidate)

    return StoragePaths(
        data_dir=data_dir,
        sqlite_db_path=sqlite_db_path,
        legacy_message_dirs=tuple(unique_candidates),
    )
