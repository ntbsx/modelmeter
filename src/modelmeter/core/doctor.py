"""Doctor diagnostics models and service."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field

from modelmeter.config.settings import AppSettings
from modelmeter.data.sqlite_inspector import SQLiteInspector
from modelmeter.data.storage import resolve_storage_paths

REQUIRED_SCHEMA: dict[str, set[str]] = {
    "session": {"id"},
    "message": {"id", "session_id", "data"},
    "part": {"id", "session_id", "data"},
    "project": {"id"},
}


class DetectedSource(BaseModel):
    """Detected data source with agent information."""

    source_id: str
    kind: Literal["sqlite", "jsonl"]
    agent: Literal["opencode", "claudecode"]
    status: Literal["ok", "error"]
    path: str
    exists: bool
    details: str | None = None


class SQLiteDiagnostics(BaseModel):
    """SQLite data source diagnostics."""

    db_path: str
    exists: bool
    can_connect: bool
    sqlite_version: str | None = None
    tables_present: list[str] = Field(default_factory=list)
    missing_tables: list[str] = Field(default_factory=list)
    missing_columns: dict[str, list[str]] = Field(default_factory=dict)
    row_counts: dict[str, int] = Field(default_factory=dict)
    error: str | None = None


class LegacyDiagnostics(BaseModel):
    """Legacy message directory diagnostics."""

    candidate_dirs: list[str] = Field(default_factory=list)
    existing_dirs: list[str] = Field(default_factory=list)


class DoctorReport(BaseModel):
    """Top-level health diagnostics payload."""

    app_name: str
    app_version: str
    opencode_data_dir: str
    claudecode_data_dir: str
    selected_source: str
    sqlite: SQLiteDiagnostics
    legacy: LegacyDiagnostics
    detected_sources: list[DetectedSource]


def _inspect_sqlite(db_path: Path) -> SQLiteDiagnostics:
    diagnostics = SQLiteDiagnostics(
        db_path=str(db_path),
        exists=db_path.exists(),
        can_connect=False,
    )

    if not diagnostics.exists:
        return diagnostics

    inspector = SQLiteInspector(db_path)
    try:
        tables = inspector.get_tables()
        diagnostics.can_connect = True
        diagnostics.sqlite_version = inspector.sqlite_version()
        diagnostics.tables_present = sorted(tables)

        missing_tables = sorted(table for table in REQUIRED_SCHEMA if table not in tables)
        diagnostics.missing_tables = missing_tables

        for table_name, required_columns in REQUIRED_SCHEMA.items():
            if table_name not in tables:
                continue
            columns = inspector.get_table_columns(table_name)
            missing_columns = sorted(required_columns - columns)
            if missing_columns:
                diagnostics.missing_columns[table_name] = missing_columns
            diagnostics.row_counts[table_name] = inspector.count_rows(table_name)

    except sqlite3.Error as exc:
        diagnostics.error = str(exc)

    return diagnostics


def _inspect_claudecode(data_dir: Path) -> DetectedSource | None:
    projects_dir = data_dir / "projects"
    if not projects_dir.exists():
        return None

    project_count = sum(1 for d in projects_dir.iterdir() if d.is_dir())
    session_count = sum(1 for _ in projects_dir.rglob("*.jsonl"))
    if session_count == 0:
        return None

    return DetectedSource(
        source_id="local-claudecode",
        kind="jsonl",
        agent="claudecode",
        status="ok",
        path=str(data_dir),
        exists=True,
        details=f"{project_count} projects, {session_count} sessions",
    )


def generate_doctor_report(
    settings: AppSettings, db_path_override: Path | None = None
) -> DoctorReport:
    """Generate diagnostics for OpenCode storage availability and schema compatibility."""
    paths = resolve_storage_paths(settings, db_path_override=db_path_override)
    sqlite_diag = _inspect_sqlite(paths.sqlite_db_path)

    candidate_dirs = [str(path) for path in paths.legacy_message_dirs]
    existing_dirs = [str(path) for path in paths.legacy_message_dirs if path.exists()]
    legacy_diag = LegacyDiagnostics(candidate_dirs=candidate_dirs, existing_dirs=existing_dirs)

    selected_source = "none"
    if sqlite_diag.can_connect and not sqlite_diag.missing_tables:
        selected_source = "sqlite"
    elif legacy_diag.existing_dirs:
        selected_source = "legacy"

    detected_sources: list[DetectedSource] = []

    if paths.sqlite_db_path.exists():
        detected_sources.append(
            DetectedSource(
                source_id="local-opencode",
                kind="sqlite",
                agent="opencode",
                status="ok",
                path=str(paths.sqlite_db_path),
                exists=True,
                details="OpenCode local data detected",
            )
        )

    claudecode_source = _inspect_claudecode(settings.claudecode_data_dir)
    if claudecode_source is not None:
        detected_sources.append(claudecode_source)

    return DoctorReport(
        app_name=settings.app_name,
        app_version=settings.app_runtime_version,
        opencode_data_dir=str(settings.opencode_data_dir),
        claudecode_data_dir=str(settings.claudecode_data_dir),
        selected_source=selected_source,
        sqlite=sqlite_diag,
        legacy=legacy_diag,
        detected_sources=detected_sources,
    )
