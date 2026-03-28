"""Tests for Claude Code JSONL data reader."""

import os
import shutil
import time
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


def test_fetch_sessions_summary_uses_file_mtime_for_filtering_and_sorting(tmp_path: Path) -> None:
    copied = tmp_path / "claude"
    shutil.copytree(FIXTURES_DIR, copied)
    repo = JsonlUsageRepository(copied)

    fresh_session = copied / "-Users-test-projs-myproject" / "session-001.jsonl"
    older_session = copied / "-Users-test-projs-myproject" / "session-002.jsonl"
    old_session_3 = copied / "-Users-test-projs-other" / "session-003.jsonl"
    old_session_4 = copied / "-Users-test-projs-myproject" / "session-004.jsonl"

    now = time.time()
    os.utime(fresh_session, (now, now))
    os.utime(older_session, (now - 3600, now - 3600))
    os.utime(old_session_3, (now - 3600, now - 3600))
    os.utime(old_session_4, (now - 3600, now - 3600))

    rows = repo.fetch_sessions_summary(min_time_updated_ms=int((now - 300) * 1000))

    assert [row["session_id"] for row in rows] == ["session-001"]
    assert rows[0]["time_updated"] >= int(now * 1000) - 1000


def test_fetch_daily_includes_interactions_at_end_of_day(tmp_path: Path) -> None:
    copied = tmp_path / "claude"
    shutil.copytree(FIXTURES_DIR, copied)
    session_dir = copied / "-Users-test-projs-boundary"
    session_dir.mkdir()
    session_file = session_dir / "session-boundary.jsonl"
    session_file.write_text(
        '{"sessionId": "session-boundary", "cwd": "/Users/test/projs/boundary", '
        '"type": "user", '
        '"message": {"role": "user", "content": [{"type": "text", "text": "late"}]}, '
        '"timestamp": "2026-03-20T23:59:58.000Z"}\n'
        '{"sessionId": "session-boundary", "cwd": "/Users/test/projs/boundary", '
        '"type": "assistant", '
        '"message": {"role": "assistant", "content": [{"type": "text", "text": "reply"}]}, '
        '"model": "claude-sonnet-4-6", "stop_reason": "end_turn", '
        '"usage": {"input_tokens": 50, "output_tokens": 25, '
        '"cache_read": 0, "cache_write": 0}, '
        '"timestamp": "2026-03-20T23:59:59.500Z"}\n'
    )
    repo = JsonlUsageRepository(copied)
    row = repo.fetch_summary_for_day(day="2026-03-20")
    assert row["input_tokens"] >= 50, (
        f"Day-boundary interaction at 23:59:59.500 missing from 2026-03-20. "
        f"Got {row['input_tokens']} input_tokens"
    )
