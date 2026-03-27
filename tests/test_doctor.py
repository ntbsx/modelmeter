from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from typer.testing import CliRunner

from modelmeter.cli.main import app
from modelmeter.config.settings import AppSettings
from modelmeter.core.doctor import generate_doctor_report


def _create_sqlite_fixture(db_path: Path, *, full_schema: bool) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE session (id TEXT PRIMARY KEY)")

        if full_schema:
            conn.execute("CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, data TEXT)")
            conn.execute("CREATE TABLE part (id TEXT PRIMARY KEY, session_id TEXT, data TEXT)")
            conn.execute("CREATE TABLE project (id TEXT PRIMARY KEY)")


def test_doctor_prefers_sqlite_when_schema_is_valid(tmp_path: Path) -> None:
    data_dir = tmp_path / "opencode"
    data_dir.mkdir()
    db_path = data_dir / "opencode.db"
    _create_sqlite_fixture(db_path, full_schema=True)

    report = generate_doctor_report(settings=AppSettings(opencode_data_dir=data_dir))

    assert report.selected_source == "sqlite"
    assert report.sqlite.can_connect is True
    assert report.sqlite.missing_tables == []


def test_doctor_reports_missing_tables(tmp_path: Path) -> None:
    data_dir = tmp_path / "opencode"
    data_dir.mkdir()
    db_path = data_dir / "opencode.db"
    _create_sqlite_fixture(db_path, full_schema=False)

    report = generate_doctor_report(settings=AppSettings(opencode_data_dir=data_dir))

    assert report.selected_source == "none"
    assert report.sqlite.can_connect is True
    assert "message" in report.sqlite.missing_tables
    assert "part" in report.sqlite.missing_tables
    assert "project" in report.sqlite.missing_tables


def test_doctor_cli_json_output(tmp_path: Path) -> None:
    data_dir = tmp_path / "opencode"
    data_dir.mkdir()
    db_path = data_dir / "opencode.db"
    _create_sqlite_fixture(db_path, full_schema=True)

    runner = CliRunner()
    result = runner.invoke(app, ["doctor", "--db-path", str(db_path), "--json"])

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["selected_source"] == "sqlite"


def test_doctor_report_includes_detected_sources(tmp_path: Path) -> None:
    data_dir = tmp_path / "opencode"
    data_dir.mkdir()
    db_path = data_dir / "opencode.db"
    _create_sqlite_fixture(db_path, full_schema=True)

    settings = AppSettings(opencode_data_dir=data_dir, claudecode_data_dir=tmp_path / ".claude")
    report = generate_doctor_report(settings=settings)

    assert hasattr(report, "detected_sources")
    assert isinstance(report.detected_sources, list)
    assert hasattr(report, "claudecode_data_dir")


def test_doctor_report_includes_agent_kinds_and_details(tmp_path: Path) -> None:
    data_dir = tmp_path / "opencode"
    data_dir.mkdir()
    db_path = data_dir / "opencode.db"
    _create_sqlite_fixture(db_path, full_schema=True)

    claudecode_dir = tmp_path / ".claude"
    projects_dir = claudecode_dir / "projects" / "-Users-test-projs-myproject"
    projects_dir.mkdir(parents=True)
    (projects_dir / "session-001.jsonl").write_text('{"type":"user"}\n', encoding="utf-8")

    report = generate_doctor_report(
        settings=AppSettings(opencode_data_dir=data_dir, claudecode_data_dir=claudecode_dir)
    )

    opencode = next(source for source in report.detected_sources if source.agent == "opencode")
    claudecode = next(source for source in report.detected_sources if source.agent == "claudecode")

    assert opencode.kind == "sqlite"
    assert opencode.status == "ok"
    assert opencode.details is not None

    assert claudecode.kind == "jsonl"
    assert claudecode.status == "ok"
    assert claudecode.path == str(claudecode_dir)
    assert claudecode.details == "1 projects, 1 sessions"
