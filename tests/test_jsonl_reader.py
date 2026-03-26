"""Tests for Claude Code JSONL data reader."""

from pathlib import Path

import pytest

from modelmeter.data.jsonl_usage_repository import JsonlUsageRepository

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "claudecode"


@pytest.fixture
def repo() -> JsonlUsageRepository:
    return JsonlUsageRepository(FIXTURES_DIR)


def test_repo_builds_index(repo: JsonlUsageRepository) -> None:
    """Repository should discover and parse session JSONL files."""
    index = repo.get_index()
    assert len(index.sessions) >= 4


def test_repo_skips_streaming_duplicates(repo: JsonlUsageRepository) -> None:
    """Records with stop_reason=null should not be counted."""
    index = repo.get_index()
    session_002 = next(s for s in index.sessions if s.session_id == "session-002")
    # Only the final record (stop_reason="end_turn") should be counted
    assert len(session_002.interactions) == 1


def test_repo_reads_cwd_for_project_path(repo: JsonlUsageRepository) -> None:
    """Project path should come from cwd field, not directory name."""
    index = repo.get_index()
    session_001 = next(s for s in index.sessions if s.session_id == "session-001")
    assert session_001.project_path == "/Users/test/projs/myproject"


def test_repo_aggregates_subagent_tokens(repo: JsonlUsageRepository) -> None:
    """Subagent tokens should be aggregated into parent session."""
    index = repo.get_index()
    session_004 = next(s for s in index.sessions if s.session_id == "session-004")
    # Should include both main session and subagent interactions
    assert len(session_004.interactions) >= 2


def test_fetch_summary(repo: JsonlUsageRepository) -> None:
    row = repo.fetch_summary()
    assert row["input_tokens"] > 0
    assert row["output_tokens"] > 0
    assert row["total_sessions"] >= 4


def test_fetch_daily(repo: JsonlUsageRepository) -> None:
    rows = repo.fetch_daily()
    assert len(rows) > 0
    for row in rows:
        assert "day" in row


def test_fetch_session_count(repo: JsonlUsageRepository) -> None:
    count = repo.fetch_session_count()
    assert count >= 4


def test_fetch_model_usage(repo: JsonlUsageRepository) -> None:
    rows = repo.fetch_model_usage()
    assert len(rows) > 0
    model_ids = [r["model_id"] for r in rows]
    assert "claude-sonnet-4-6" in model_ids


def test_fetch_model_usage_detail(repo: JsonlUsageRepository) -> None:
    rows = repo.fetch_model_usage_detail()
    assert len(rows) > 0
    for row in rows:
        assert "total_interactions" in row


def test_fetch_project_usage_detail(repo: JsonlUsageRepository) -> None:
    rows = repo.fetch_project_usage_detail()
    assert len(rows) >= 2


def test_fetch_sessions_summary(repo: JsonlUsageRepository) -> None:
    rows = repo.fetch_sessions_summary()
    assert len(rows) >= 4
