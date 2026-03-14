from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime, timedelta
from pathlib import Path

from typer.testing import CliRunner

from modelmeter.cli.main import app
from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import (
    get_daily,
    get_model_detail,
    get_models,
    get_providers,
    get_project_detail,
    get_projects,
    get_summary,
)


def _create_usage_fixture(db_path: Path) -> None:
    now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    yesterday_ms = int((datetime.now(tz=UTC) - timedelta(days=1)).timestamp() * 1000)

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE session ("
            "id TEXT PRIMARY KEY, "
            "project_id TEXT, "
            "title TEXT, "
            "directory TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "time_archived INTEGER"
            ")"
        )
        conn.execute("CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT, name TEXT)")
        conn.execute("CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, data TEXT)")
        conn.execute(
            "CREATE TABLE part ("
            "id TEXT PRIMARY KEY, "
            "message_id TEXT, "
            "session_id TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "data TEXT"
            ")"
        )

        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p1", "Session One", "/tmp/project-one", now_ms, now_ms, None),
        )
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "s2",
                "p1",
                "Session Two",
                "/tmp/project-one",
                yesterday_ms,
                yesterday_ms,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO project (id, worktree, name) VALUES (?, ?, ?)",
            ("p1", "/tmp/project-one", "project-one"),
        )

        assistant_today = {
            "role": "assistant",
            "modelID": "anthropic/claude-sonnet-4-5",
            "time": {"created": now_ms},
            "tokens": {
                "input": 10,
                "output": 5,
                "cache": {"read": 3, "write": 2},
            },
        }
        assistant_yesterday = {
            "role": "assistant",
            "modelID": "anthropic/claude-sonnet-4-5",
            "time": {"created": yesterday_ms},
            "tokens": {
                "input": 7,
                "output": 1,
                "cache": {"read": 0, "write": 0},
            },
        }
        user_message = {
            "role": "user",
            "time": {"created": now_ms},
            "tokens": {},
        }

        conn.execute(
            "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
            ("m1", "s1", json.dumps(assistant_today)),
        )
        conn.execute(
            "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
            ("m2", "s2", json.dumps(assistant_yesterday)),
        )
        conn.execute(
            "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
            ("m3", "s1", json.dumps(user_message)),
        )


def _insert_step_finish(
    db_path: Path,
    *,
    session_id: str,
    created_ms: int,
    input_tokens: int,
    output_tokens: int,
    cache_read: int,
    cache_write: int,
) -> None:
    with sqlite3.connect(db_path) as conn:
        payload = {
            "type": "step-finish",
            "tokens": {
                "input": input_tokens,
                "output": output_tokens,
                "cache": {"read": cache_read, "write": cache_write},
            },
        }
        conn.execute(
            "INSERT INTO part (id, message_id, session_id, time_created, time_updated, data) "
            "VALUES (?, ?, ?, ?, ?, ?)",
            (
                f"p-{session_id}",
                "m1",
                session_id,
                created_ms,
                created_ms,
                json.dumps(payload),
            ),
        )


def _create_pricing_fixture(path: Path) -> None:
    payload = {
        "anthropic/claude-sonnet-4-5": {
            "input": 1.0,
            "output": 2.0,
            "cache_read": 0.5,
            "cache_write": 1.5,
        }
    }
    path.write_text(json.dumps(payload))


def _create_provider_fixture(db_path: Path) -> None:
    now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE session ("
            "id TEXT PRIMARY KEY, "
            "project_id TEXT, "
            "title TEXT, "
            "directory TEXT, "
            "time_created INTEGER, "
            "time_updated INTEGER, "
            "time_archived INTEGER"
            ")"
        )
        conn.execute("CREATE TABLE project (id TEXT PRIMARY KEY, worktree TEXT, name TEXT)")
        conn.execute("CREATE TABLE message (id TEXT PRIMARY KEY, session_id TEXT, data TEXT)")
        conn.execute(
            "INSERT INTO session "
            "(id, project_id, title, directory, time_created, time_updated, time_archived) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("s1", "p1", "Provider Session", "/tmp/providers", now_ms, now_ms, None),
        )

        conn.execute(
            "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
            (
                "m1",
                "s1",
                json.dumps(
                    {
                        "role": "assistant",
                        "modelID": "anthropic/claude-sonnet-4-5",
                        "time": {"created": now_ms},
                        "tokens": {"input": 10, "output": 1, "cache": {"read": 0, "write": 0}},
                    }
                ),
            ),
        )
        conn.execute(
            "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
            (
                "m2",
                "s1",
                json.dumps(
                    {
                        "role": "assistant",
                        "modelID": "openai/gpt-5",
                        "time": {"created": now_ms},
                        "tokens": {"input": 8, "output": 2, "cache": {"read": 0, "write": 0}},
                    }
                ),
            ),
        )


def test_get_summary_aggregates_tokens(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    result = get_summary(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
    )

    assert result.total_sessions == 2
    assert result.usage.input_tokens == 17
    assert result.usage.output_tokens == 6
    assert result.usage.cache_read_tokens == 3
    assert result.usage.cache_write_tokens == 2


def test_get_daily_returns_two_days(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    result = get_daily(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
    )

    assert len(result.daily) == 2
    assert result.totals.input_tokens == 17
    assert result.totals.output_tokens == 6


def test_get_summary_calculates_cost_when_pricing_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_summary(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
    )

    assert result.cost_usd == 0.0000335
    assert result.pricing_source == str(pricing_path)


def test_get_daily_calculates_cost_when_pricing_exists(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_daily(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
    )

    assert result.total_cost_usd == 0.0000335
    assert result.pricing_source == str(pricing_path)
    assert result.daily[0].cost_usd is not None
    assert result.daily[1].cost_usd is not None


def test_summary_command_json_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "summary",
            "--db-path",
            str(db_path),
            "--pricing-file",
            str(pricing_path),
            "--days",
            "7",
            "--json",
        ],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_sessions"] == 2
    assert payload["usage"]["input_tokens"] == 17
    assert payload["cost_usd"] == 0.0000335


def test_summary_uses_steps_when_requested(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)
    now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    _insert_step_finish(
        db_path,
        session_id="s1",
        created_ms=now_ms,
        input_tokens=100,
        output_tokens=50,
        cache_read=25,
        cache_write=10,
    )

    result = get_summary(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        token_source="steps",
    )

    assert result.total_sessions == 2
    assert result.usage.input_tokens == 100
    assert result.usage.output_tokens == 50


def test_summary_can_use_activity_session_count_source(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)
    now_ms = int(datetime.now(tz=UTC).timestamp() * 1000)
    _insert_step_finish(
        db_path,
        session_id="s1",
        created_ms=now_ms,
        input_tokens=100,
        output_tokens=50,
        cache_read=25,
        cache_write=10,
    )

    result = get_summary(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        token_source="steps",
        session_count_source="activity",
    )

    assert result.total_sessions == 1


def test_get_models_returns_model_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_models(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
        limit=10,
    )

    assert len(result.models) == 1
    assert result.models[0].model_id == "anthropic/claude-sonnet-4-5"
    assert result.models[0].total_interactions == 2
    assert result.models[0].cost_usd == 0.0000335


def test_get_model_detail_returns_daily_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_model_detail(
        settings=AppSettings(opencode_data_dir=tmp_path),
        model_id="anthropic/claude-sonnet-4-5",
        days=7,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
    )

    assert result.total_interactions == 2
    assert result.total_sessions == 2
    assert len(result.daily) == 2
    assert result.cost_usd == 0.0000335


def test_models_command_json_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["models", "--db-path", str(db_path), "--days", "7", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["models"]) == 1
    assert payload["models"][0]["model_id"] == "anthropic/claude-sonnet-4-5"


def test_model_command_json_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["model", "anthropic/claude-sonnet-4-5", "--db-path", str(db_path), "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["model_id"] == "anthropic/claude-sonnet-4-5"
    assert payload["total_interactions"] == 2


def test_get_model_detail_falls_back_to_providerless_id(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    result = get_model_detail(
        settings=AppSettings(opencode_data_dir=tmp_path),
        model_id="any-provider/anthropic/claude-sonnet-4-5",
        days=7,
        db_path_override=db_path,
    )

    assert result.model_id == "anthropic/claude-sonnet-4-5"
    assert result.total_interactions == 2


def test_get_projects_returns_project_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_projects(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
        limit=10,
    )

    assert len(result.projects) == 1
    assert result.projects[0].project_id == "p1"
    assert result.projects[0].total_interactions == 2
    assert result.projects[0].cost_usd == 0.0000335


def test_projects_command_json_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["projects", "--db-path", str(db_path), "--days", "7", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert len(payload["projects"]) == 1
    assert payload["projects"][0]["project_id"] == "p1"


def test_get_project_detail_returns_sessions_sorted_by_last_updated(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_project_detail(
        settings=AppSettings(opencode_data_dir=tmp_path),
        project_id="p1",
        days=7,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
    )

    assert result.project_id == "p1"
    assert result.total_sessions == 2
    assert result.sessions_returned == 2
    assert result.sessions[0].session_id == "s1"
    assert result.sessions[1].session_id == "s2"
    assert result.total_interactions == 2
    assert result.total_cost_usd == 0.0000335


def test_get_project_detail_applies_session_pagination(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    pricing_path = tmp_path / "models.json"
    _create_usage_fixture(db_path)
    _create_pricing_fixture(pricing_path)

    result = get_project_detail(
        settings=AppSettings(opencode_data_dir=tmp_path),
        project_id="p1",
        days=7,
        session_offset=1,
        session_limit=1,
        db_path_override=db_path,
        pricing_file_override=pricing_path,
    )

    assert result.total_sessions == 2
    assert result.sessions_offset == 1
    assert result.sessions_limit == 1
    assert result.sessions_returned == 1
    assert len(result.sessions) == 1
    assert result.sessions[0].session_id == "s2"


def test_get_project_detail_raises_when_project_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_usage_fixture(db_path)

    try:
        get_project_detail(
            settings=AppSettings(opencode_data_dir=tmp_path),
            project_id="missing",
            days=7,
            db_path_override=db_path,
        )
    except RuntimeError as exc:
        assert str(exc) == "No data found for project 'missing'."
    else:
        raise AssertionError("Expected RuntimeError for missing project")


def test_get_providers_returns_provider_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_provider_fixture(db_path)

    result = get_providers(
        settings=AppSettings(opencode_data_dir=tmp_path),
        days=7,
        db_path_override=db_path,
        limit=10,
    )

    assert len(result.providers) == 2
    assert result.total_providers == 2
    providers = {row.provider for row in result.providers}
    assert providers == {"anthropic", "openai"}


def test_providers_command_json_output(tmp_path: Path) -> None:
    db_path = tmp_path / "opencode.db"
    _create_provider_fixture(db_path)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["providers", "--db-path", str(db_path), "--days", "7", "--json"],
    )

    assert result.exit_code == 0
    payload = json.loads(result.stdout)
    assert payload["total_providers"] == 2
    assert len(payload["providers"]) == 2
