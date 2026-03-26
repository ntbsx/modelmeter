"""Tests for multi-agent local source resolution and merging."""

from pathlib import Path
from unittest.mock import patch

from modelmeter.config.settings import AppSettings


def test_resolve_local_repositories_opencode_only(tmp_path: Path) -> None:
    """When only OpenCode is available, return one repository."""
    from modelmeter.core.analytics import _resolve_local_repositories

    db_path = tmp_path / "opencode.db"
    db_path.touch()

    settings = AppSettings(
        opencode_data_dir=tmp_path,
        opencode_db_path=db_path,
        claudecode_enabled=False,
    )

    with patch("modelmeter.core.analytics._resolve_sqlite_path", return_value=db_path):
        repos = _resolve_local_repositories(settings)
    assert len(repos) == 1
    assert repos[0][0] == "local-opencode"


def test_resolve_local_repositories_claudecode_only(tmp_path: Path) -> None:
    """When only Claude Code is available, return one repository."""
    from modelmeter.core.analytics import _resolve_local_repositories

    projects_dir = tmp_path / "claudecode" / "projects" / "-test-proj"
    projects_dir.mkdir(parents=True)
    (projects_dir / "session.jsonl").write_text('{"type":"user"}\n')

    settings = AppSettings(
        opencode_data_dir=tmp_path / "nonexistent",
        claudecode_data_dir=tmp_path / "claudecode",
        claudecode_enabled=True,
    )

    repos = _resolve_local_repositories(settings)
    assert len(repos) == 1
    assert repos[0][0] == "local-claudecode"
