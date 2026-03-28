"""Tests for multi-agent local source resolution and merging."""

from datetime import date
from pathlib import Path
from typing import Any
from unittest.mock import patch

from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import _canonical_project_id
from modelmeter.core.pricing import ModelPricing


class _FakeSummaryRepo:
    def __init__(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cache_write: int,
        total_sessions: int,
        model_id: str,
    ) -> None:
        self._summary = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "total_sessions": total_sessions,
        }
        self._models = [
            {
                "model_id": model_id,
                "provider_id": "anthropic",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
            }
        ]

    def fetch_summary_steps(self, *, days: int | None = None) -> dict[str, int]:
        return self._summary

    def fetch_summary(self, *, days: int | None = None) -> dict[str, int]:
        return self._summary

    def fetch_session_count(self, *, days: int | None = None) -> int:
        return int(self._summary["total_sessions"])

    def fetch_model_usage(self, *, days: int | None = None) -> list[dict[str, Any]]:
        return self._models


class _FakeDailyRepo:
    def __init__(
        self,
        *,
        day: str,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cache_write: int,
        total_sessions: int,
        model_id: str = "anthropic/claude-sonnet-4-5",
        provider_id: str = "anthropic",
    ) -> None:
        self._day = day
        self._daily_rows = [
            {
                "day": day,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
                "total_sessions": total_sessions,
            }
        ]
        self._summary = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": cache_read,
            "cache_write": cache_write,
            "total_sessions": total_sessions,
        }
        self._daily_model_rows = [
            {
                "day": day,
                "model_id": model_id,
                "provider_id": provider_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
                "total_sessions": total_sessions,
            }
        ]

    def resolve_token_source(self, *, days: int | None = None, token_source: str = "auto") -> str:
        return "message"

    def resolve_session_count_source(
        self, *, days: int | None = None, session_count_source: str = "auto"
    ) -> str:
        return "session"

    def fetch_daily(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[dict[str, Any]]:
        return self._daily_rows

    def fetch_summary(self, *, days: int | None = None) -> dict[str, int]:
        return self._summary

    def fetch_daily_session_counts(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> dict[str, int]:
        return {self._day: int(self._summary["total_sessions"])}

    def fetch_session_count(self, *, days: int | None = None) -> int:
        return int(self._summary["total_sessions"])

    def fetch_daily_model_usage(
        self, *, days: int | None = None, timezone_offset_minutes: int = 0
    ) -> list[dict[str, Any]]:
        return self._daily_model_rows


class _FakeModelsRepo:
    def __init__(
        self,
        *,
        model_id: str,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cache_write: int,
        total_sessions: int,
        total_interactions: int,
        summary_input_tokens: int | None = None,
        summary_output_tokens: int | None = None,
        summary_cache_read: int | None = None,
        summary_cache_write: int | None = None,
        summary_total_sessions: int | None = None,
        steps_input_tokens: int | None = None,
        steps_output_tokens: int | None = None,
        steps_cache_read: int | None = None,
        steps_cache_write: int | None = None,
        steps_total_sessions: int | None = None,
        resolved_token_source: str = "message",
        resolved_session_count_source: str = "session",
        session_count: int | None = None,
    ) -> None:
        self._rows = [
            {
                "model_id": model_id,
                "provider_id": provider_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
                "total_sessions": total_sessions,
                "total_interactions": total_interactions,
            }
        ]
        self._summary = {
            "input_tokens": summary_input_tokens
            if summary_input_tokens is not None
            else input_tokens,
            "output_tokens": summary_output_tokens
            if summary_output_tokens is not None
            else output_tokens,
            "cache_read": summary_cache_read if summary_cache_read is not None else cache_read,
            "cache_write": summary_cache_write if summary_cache_write is not None else cache_write,
            "total_sessions": summary_total_sessions
            if summary_total_sessions is not None
            else total_sessions,
        }
        self._steps_summary = {
            "input_tokens": steps_input_tokens if steps_input_tokens is not None else input_tokens,
            "output_tokens": steps_output_tokens
            if steps_output_tokens is not None
            else output_tokens,
            "cache_read": steps_cache_read if steps_cache_read is not None else cache_read,
            "cache_write": steps_cache_write if steps_cache_write is not None else cache_write,
            "total_sessions": steps_total_sessions
            if steps_total_sessions is not None
            else total_sessions,
        }
        self._resolved_token_source = resolved_token_source
        self._resolved_session_count_source = resolved_session_count_source
        self._session_count = session_count if session_count is not None else total_sessions

    def fetch_model_usage_detail(self, *, days: int | None = None) -> list[dict[str, Any]]:
        return self._rows

    def fetch_summary(self, *, days: int | None = None) -> dict[str, int]:
        return self._summary

    def fetch_summary_steps(self, *, days: int | None = None) -> dict[str, int]:
        return self._steps_summary

    def resolve_token_source(self, *, days: int | None = None, token_source: str = "auto") -> str:
        return self._resolved_token_source if token_source in {"auto", "steps"} else token_source

    def resolve_session_count_source(
        self, *, days: int | None = None, session_count_source: str = "auto"
    ) -> str:
        return (
            self._resolved_session_count_source
            if session_count_source in {"auto", "activity"}
            else session_count_source
        )

    def fetch_session_count(self, *, days: int | None = None) -> int:
        return self._session_count


class _FakeProjectsRepo:
    def __init__(
        self,
        *,
        project_id: str,
        project_name: str,
        project_path: str,
        model_id: str,
        input_tokens: int,
        output_tokens: int,
        cache_read: int,
        cache_write: int,
        total_sessions: int,
        total_interactions: int,
        summary_input_tokens: int | None = None,
        summary_output_tokens: int | None = None,
        summary_cache_read: int | None = None,
        summary_cache_write: int | None = None,
        summary_total_sessions: int | None = None,
        steps_input_tokens: int | None = None,
        steps_output_tokens: int | None = None,
        steps_cache_read: int | None = None,
        steps_cache_write: int | None = None,
        steps_total_sessions: int | None = None,
        resolved_token_source: str = "message",
        resolved_session_count_source: str = "session",
        session_count: int | None = None,
    ) -> None:
        self._project_rows = [
            {
                "project_id": project_id,
                "project_name": project_name,
                "project_path": project_path,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
                "total_sessions": total_sessions,
                "total_interactions": total_interactions,
            }
        ]
        self._summary = {
            "input_tokens": summary_input_tokens
            if summary_input_tokens is not None
            else input_tokens,
            "output_tokens": summary_output_tokens
            if summary_output_tokens is not None
            else output_tokens,
            "cache_read": summary_cache_read if summary_cache_read is not None else cache_read,
            "cache_write": summary_cache_write if summary_cache_write is not None else cache_write,
            "total_sessions": summary_total_sessions
            if summary_total_sessions is not None
            else total_sessions,
        }
        self._steps_summary = {
            "input_tokens": steps_input_tokens if steps_input_tokens is not None else input_tokens,
            "output_tokens": steps_output_tokens
            if steps_output_tokens is not None
            else output_tokens,
            "cache_read": steps_cache_read if steps_cache_read is not None else cache_read,
            "cache_write": steps_cache_write if steps_cache_write is not None else cache_write,
            "total_sessions": steps_total_sessions
            if steps_total_sessions is not None
            else total_sessions,
        }
        self._resolved_token_source = resolved_token_source
        self._resolved_session_count_source = resolved_session_count_source
        self._session_count = session_count if session_count is not None else total_sessions
        self._project_model_rows = [
            {
                "project_id": project_id,
                "model_id": model_id,
                "provider_id": "anthropic",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": cache_read,
                "cache_write": cache_write,
            }
        ]

    def fetch_project_usage_detail(self, *, days: int | None = None) -> list[dict[str, Any]]:
        return self._project_rows

    def fetch_summary(self, *, days: int | None = None) -> dict[str, int]:
        return self._summary

    def fetch_summary_steps(self, *, days: int | None = None) -> dict[str, int]:
        return self._steps_summary

    def resolve_token_source(self, *, days: int | None = None, token_source: str = "auto") -> str:
        return self._resolved_token_source if token_source in {"auto", "steps"} else token_source

    def resolve_session_count_source(
        self, *, days: int | None = None, session_count_source: str = "auto"
    ) -> str:
        return (
            self._resolved_session_count_source
            if session_count_source in {"auto", "activity"}
            else session_count_source
        )

    def fetch_session_count(self, *, days: int | None = None) -> int:
        return self._session_count

    def fetch_project_model_usage(self, *, days: int | None = None) -> list[dict[str, Any]]:
        return self._project_model_rows


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


def test_get_summary_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_summary

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeSummaryRepo(
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
                model_id="anthropic/claude-sonnet-4-5",
            ),
        ),
        (
            "local-claudecode",
            _FakeSummaryRepo(
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_summary(settings=settings)

    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 12
    assert result.usage.cache_read_tokens == 5
    assert result.usage.cache_write_tokens == 5
    assert result.total_sessions == 3
    assert result.source_scope == "local"
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_summary_prices_providerless_model_ids() -> None:
    from modelmeter.core.analytics import get_summary

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeSummaryRepo(
                input_tokens=10,
                output_tokens=5,
                cache_read=0,
                cache_write=0,
                total_sessions=1,
                model_id="anthropic/claude-sonnet-4-6",
            ),
        ),
        (
            "local-claudecode",
            _FakeSummaryRepo(
                input_tokens=20,
                output_tokens=7,
                cache_read=0,
                cache_write=0,
                total_sessions=2,
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]
    pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}

    with (
        patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos),
        patch("modelmeter.core.analytics.load_pricing_book", return_value=(pricing_book, "test")),
    ):
        result = get_summary(settings=settings)

    assert result.cost_usd is not None
    assert result.cost_usd > 0


def test_get_daily_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_daily

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeDailyRepo(
                day="2026-03-27",
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
            ),
        ),
        (
            "local-claudecode",
            _FakeDailyRepo(
                day="2026-03-27",
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_daily(settings=settings)

    assert result.totals.input_tokens == 30
    assert result.totals.output_tokens == 12
    assert result.totals.cache_read_tokens == 5
    assert result.totals.cache_write_tokens == 5
    assert result.total_sessions == 3
    assert len(result.daily) == 1
    assert result.daily[0].day == date(2026, 3, 27)
    assert result.daily[0].usage.input_tokens == 30
    assert result.daily[0].total_sessions == 3
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_daily_prices_providerless_model_ids() -> None:
    from modelmeter.core.analytics import get_daily

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeDailyRepo(
                day="2026-03-27",
                input_tokens=10,
                output_tokens=5,
                cache_read=0,
                cache_write=0,
                total_sessions=1,
                model_id="anthropic/claude-sonnet-4-6",
            ),
        ),
        (
            "local-claudecode",
            _FakeDailyRepo(
                day="2026-03-27",
                input_tokens=20,
                output_tokens=7,
                cache_read=0,
                cache_write=0,
                total_sessions=2,
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]
    pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}

    with (
        patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos),
        patch("modelmeter.core.analytics.load_pricing_book", return_value=(pricing_book, "test")),
    ):
        result = get_daily(settings=settings)

    assert result.total_cost_usd is not None
    assert result.daily[0].cost_usd is not None


def test_get_models_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_models

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-5",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-5",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_models(settings=settings, limit=0)

    assert result.totals.input_tokens == 30
    assert result.totals.output_tokens == 12
    assert result.totals.cache_read_tokens == 5
    assert result.totals.cache_write_tokens == 5
    assert result.total_sessions == 3
    assert result.total_models == 1
    assert result.models_returned == 1
    assert result.models[0].provider == "anthropic"
    assert result.models[0].usage.input_tokens == 30
    assert result.models[0].total_sessions == 3
    assert result.models[0].total_interactions == 7
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_models_normalizes_providerless_ids_across_local_sources() -> None:
    from modelmeter.core.analytics import get_models

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                cache_read=0,
                cache_write=0,
                total_sessions=1,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeModelsRepo(
                model_id="claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                cache_read=0,
                cache_write=0,
                total_sessions=2,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_models(settings=settings, limit=0)

    assert result.total_models == 1
    assert result.models[0].model_id == "anthropic/claude-sonnet-4-6"
    assert result.models[0].provider == "anthropic"
    assert result.models[0].usage.input_tokens == 30
    assert result.models[0].usage.output_tokens == 12
    assert result.models[0].total_sessions == 3
    assert result.models[0].total_interactions == 7


def test_get_providers_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_providers

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-5",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_providers(settings=settings, limit=0)

    assert result.totals.input_tokens == 30
    assert result.totals.output_tokens == 12
    assert result.totals.cache_read_tokens == 5
    assert result.totals.cache_write_tokens == 5
    assert result.total_sessions == 3
    assert result.total_providers == 1
    assert result.providers_returned == 1
    assert result.providers[0].provider == "anthropic"
    assert result.providers[0].usage.input_tokens == 30
    assert result.providers[0].total_models == 2
    assert result.providers[0].total_interactions == 7
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_providers_prices_providerless_model_ids() -> None:
    from modelmeter.core.analytics import get_providers

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                cache_read=0,
                cache_write=0,
                total_sessions=1,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeModelsRepo(
                model_id="claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                cache_read=0,
                cache_write=0,
                total_sessions=2,
                total_interactions=4,
            ),
        ),
    ]
    pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}

    with (
        patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos),
        patch("modelmeter.core.analytics.load_pricing_book", return_value=(pricing_book, "test")),
    ):
        result = get_providers(settings=settings, limit=0)

    assert result.total_cost_usd is not None
    assert result.providers[0].cost_usd is not None


def test_get_projects_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_projects

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeProjectsRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                model_id="anthropic/claude-sonnet-4-5",
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeProjectsRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                model_id="anthropic/claude-sonnet-4-6",
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_projects(settings=settings, limit=0)

    assert result.totals.input_tokens == 30
    assert result.totals.output_tokens == 12
    assert result.totals.cache_read_tokens == 5
    assert result.totals.cache_write_tokens == 5
    assert result.total_sessions == 3
    assert result.total_projects == 1
    assert result.projects_returned == 1
    assert result.projects[0].project_id == _canonical_project_id("p1", "/tmp/demo")
    assert result.projects[0].usage.input_tokens == 30
    assert result.projects[0].total_sessions == 3
    assert result.projects[0].total_interactions == 7
    assert sorted(result.projects[0].sources) == ["local-claudecode", "local-opencode"]
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_multi_local_aggregates_use_resolved_steps_summary_for_totals() -> None:
    from modelmeter.core.analytics import get_models, get_projects, get_providers

    settings = AppSettings()
    model_repos = [
        (
            "local-opencode",
            _FakeModelsRepo(
                model_id="anthropic/claude-sonnet-4-5",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
                total_interactions=3,
                summary_input_tokens=100,
                summary_output_tokens=50,
                summary_cache_read=20,
                summary_cache_write=10,
                summary_total_sessions=9,
                steps_input_tokens=10,
                steps_output_tokens=5,
                steps_cache_read=2,
                steps_cache_write=1,
                steps_total_sessions=1,
                resolved_token_source="steps",
                resolved_session_count_source="activity",
                session_count=9,
            ),
        ),
        (
            "local-claudecode",
            _FakeModelsRepo(
                model_id="claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
                total_interactions=4,
                resolved_token_source="message",
                resolved_session_count_source="activity",
                session_count=2,
            ),
        ),
    ]
    project_repos = [
        (
            "local-opencode",
            _FakeProjectsRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                model_id="anthropic/claude-sonnet-4-5",
                input_tokens=10,
                output_tokens=5,
                cache_read=2,
                cache_write=1,
                total_sessions=1,
                total_interactions=3,
                summary_input_tokens=100,
                summary_output_tokens=50,
                summary_cache_read=20,
                summary_cache_write=10,
                summary_total_sessions=9,
                steps_input_tokens=10,
                steps_output_tokens=5,
                steps_cache_read=2,
                steps_cache_write=1,
                steps_total_sessions=1,
                resolved_token_source="steps",
                resolved_session_count_source="activity",
                session_count=9,
            ),
        ),
        (
            "local-claudecode",
            _FakeProjectsRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                model_id="claude-sonnet-4-6",
                input_tokens=20,
                output_tokens=7,
                cache_read=3,
                cache_write=4,
                total_sessions=2,
                total_interactions=4,
                resolved_token_source="message",
                resolved_session_count_source="activity",
                session_count=2,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=model_repos):
        models = get_models(
            settings=settings,
            limit=0,
            token_source="steps",
            session_count_source="activity",
        )
        providers = get_providers(
            settings=settings,
            limit=0,
            token_source="steps",
            session_count_source="activity",
        )

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=project_repos):
        projects = get_projects(
            settings=settings,
            limit=0,
            token_source="steps",
            session_count_source="activity",
        )

    assert models.totals.input_tokens == 30
    assert models.totals.output_tokens == 12
    assert models.totals.cache_read_tokens == 5
    assert models.totals.cache_write_tokens == 5
    assert models.total_sessions == 3

    assert providers.totals.input_tokens == 30
    assert providers.totals.output_tokens == 12
    assert providers.totals.cache_read_tokens == 5
    assert providers.totals.cache_write_tokens == 5
    assert providers.total_sessions == 3

    assert projects.totals.input_tokens == 30
    assert projects.totals.output_tokens == 12
    assert projects.totals.cache_read_tokens == 5
    assert projects.totals.cache_write_tokens == 5
    assert projects.total_sessions == 3


class _FakeDateInsightsRepo:
    def __init__(
        self,
        *,
        input_tokens: int,
        output_tokens: int,
        total_sessions: int,
        total_interactions: int,
        model_id: str,
        session_id: str | None = None,
        project_id: str = "p1",
        project_name: str = "demo",
        started_at_ms: int = 1000,
    ) -> None:
        self._summary_row = {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": 0,
            "cache_write": 0,
            "total_sessions": total_sessions,
            "total_interactions": total_interactions,
        }
        self._model_rows = [
            {
                "model_id": model_id,
                "provider_id": "anthropic",
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": 0,
                "cache_write": 0,
                "total_sessions": total_sessions,
                "total_interactions": total_interactions,
            }
        ]
        self._project_rows: list[dict[str, Any]] = []
        self._project_model_rows: list[dict[str, Any]] = []
        self._session_model_rows: list[dict[str, Any]] = []
        if session_id is not None:
            self._session_model_rows = [
                {
                    "session_id": session_id,
                    "session_title": f"session-{session_id}",
                    "project_id": project_id,
                    "project_name": project_name,
                    "model_id": model_id,
                    "provider_id": "anthropic",
                    "input_tokens": input_tokens,
                    "output_tokens": output_tokens,
                    "cache_read": 0,
                    "cache_write": 0,
                    "total_interactions": total_interactions,
                    "started_at_ms": started_at_ms,
                }
            ]

    def fetch_summary_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> dict[str, Any]:
        return self._summary_row

    def fetch_summary_for_day_steps(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> dict[str, Any] | None:
        return None

    def fetch_model_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[dict[str, Any]]:
        return self._model_rows

    def fetch_project_usage_detail_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[dict[str, Any]]:
        return self._project_rows

    def fetch_project_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[dict[str, Any]]:
        return self._project_model_rows

    def fetch_session_model_usage_for_day(
        self, *, day: str, timezone_offset_minutes: int = 0
    ) -> list[dict[str, Any]]:
        return self._session_model_rows


def test_get_date_insights_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_date_insights

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeDateInsightsRepo(
                input_tokens=10,
                output_tokens=5,
                total_sessions=1,
                total_interactions=3,
                model_id="anthropic/claude-sonnet-4-5",
            ),
        ),
        (
            "local-claudecode",
            _FakeDateInsightsRepo(
                input_tokens=20,
                output_tokens=7,
                total_sessions=2,
                total_interactions=4,
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_date_insights(settings=settings, day=date(2026, 3, 27))

    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 12
    assert result.total_sessions == 3
    assert result.total_interactions == 7
    assert len(result.models) == 2
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_date_insights_normalizes_and_merges_providerless_model_ids() -> None:
    from modelmeter.core.analytics import get_date_insights

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeDateInsightsRepo(
                input_tokens=10,
                output_tokens=5,
                total_sessions=1,
                total_interactions=3,
                model_id="anthropic/claude-sonnet-4-6",
            ),
        ),
        (
            "local-claudecode",
            _FakeDateInsightsRepo(
                input_tokens=20,
                output_tokens=7,
                total_sessions=2,
                total_interactions=4,
                model_id="claude-sonnet-4-6",
            ),
        ),
    ]
    pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}

    with (
        patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos),
        patch("modelmeter.core.analytics.load_pricing_book", return_value=(pricing_book, "test")),
    ):
        result = get_date_insights(settings=settings, day=date(2026, 3, 27))

    assert len(result.models) == 1
    assert result.models[0].model_id == "anthropic/claude-sonnet-4-6"
    assert result.models[0].usage.input_tokens == 30
    assert result.models[0].cost_usd is not None


def test_get_date_insights_namespaces_colliding_session_ids_across_local_sources() -> None:
    from modelmeter.core.analytics import get_date_insights

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeDateInsightsRepo(
                input_tokens=10,
                output_tokens=5,
                total_sessions=1,
                total_interactions=3,
                model_id="anthropic/claude-sonnet-4-5",
                session_id="session-001",
                started_at_ms=1000,
            ),
        ),
        (
            "local-claudecode",
            _FakeDateInsightsRepo(
                input_tokens=20,
                output_tokens=7,
                total_sessions=1,
                total_interactions=4,
                model_id="claude-sonnet-4-6",
                session_id="session-001",
                started_at_ms=2000,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_date_insights(settings=settings, day=date(2026, 3, 27))

    session_ids = {session.session_id for session in result.sessions}
    assert session_ids == {"local-opencode:session-001", "local-claudecode:session-001"}
    assert len(result.sessions) == 2


class _FakeModelDetailRepo:
    def __init__(
        self,
        *,
        model_id: str,
        provider_id: str,
        input_tokens: int,
        output_tokens: int,
        total_sessions: int,
        total_interactions: int,
        day: str = "2026-03-27",
    ) -> None:
        self._detail_row = {
            "model_id": model_id,
            "provider_id": provider_id,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cache_read": 0,
            "cache_write": 0,
            "total_sessions": total_sessions,
            "total_interactions": total_interactions,
        }
        self._daily_rows = [
            {
                "day": day,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": 0,
                "cache_write": 0,
                "total_sessions": total_sessions,
            }
        ]

    def fetch_model_detail(
        self, *, model_id: str, days: int | None = None
    ) -> dict[str, Any] | None:
        if model_id == self._detail_row["model_id"]:
            return self._detail_row
        return None

    def fetch_daily_model_detail(
        self, *, model_id: str, days: int | None = None
    ) -> list[dict[str, Any]]:
        if model_id == self._detail_row["model_id"]:
            return self._daily_rows
        return []


def test_get_model_detail_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_model_detail

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeModelDetailRepo(
                model_id="anthropic/claude-sonnet-4-5",
                provider_id="anthropic",
                input_tokens=10,
                output_tokens=5,
                total_sessions=1,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeModelDetailRepo(
                model_id="anthropic/claude-sonnet-4-5",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                total_sessions=2,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_model_detail(settings=settings, model_id="anthropic/claude-sonnet-4-5")

    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 12
    assert result.total_sessions == 3
    assert result.total_interactions == 7
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


class _FakeProjectDetailRepo:
    def __init__(
        self,
        *,
        project_id: str,
        project_name: str,
        project_path: str | None,
        session_id: str,
        model_id: str = "anthropic/claude-sonnet-4-5",
        provider_id: str = "anthropic",
        input_tokens: int,
        output_tokens: int,
        total_interactions: int,
        last_updated_ms: int = 1000,
    ) -> None:
        self._project_id = project_id
        self._project_name = project_name
        self._project_path = project_path
        self._session_rows = [
            {
                "session_id": session_id,
                "title": f"session-{session_id}",
                "directory": "/tmp",
                "last_updated_ms": last_updated_ms,
                "project_id": project_id,
                "project_name": project_name,
                "project_path": project_path,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": 0,
                "cache_write": 0,
                "total_interactions": total_interactions,
            }
        ]
        self._session_model_rows = [
            {
                "session_id": session_id,
                "model_id": model_id,
                "provider_id": provider_id,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cache_read": 0,
                "cache_write": 0,
                "total_interactions": total_interactions,
            }
        ]

    def fetch_project_session_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[dict[str, Any]]:
        if project_id == self._project_id:
            return self._session_rows
        return []

    def fetch_project_session_model_usage(
        self, *, project_id: str, days: int | None = None
    ) -> list[dict[str, Any]]:
        if project_id == self._project_id:
            return self._session_model_rows
        return []

    def fetch_project_usage_detail(self, *, days: int | None = None) -> list[dict[str, Any]]:
        return [
            {
                "project_id": self._project_id,
                "project_name": self._project_name,
                "project_path": self._project_path,
                "input_tokens": self._session_rows[0]["input_tokens"],
                "output_tokens": self._session_rows[0]["output_tokens"],
                "cache_read": 0,
                "cache_write": 0,
                "total_sessions": 1,
                "total_interactions": self._session_rows[0]["total_interactions"],
            }
        ]


def test_get_project_detail_merges_local_sources() -> None:
    from modelmeter.core.analytics import get_project_detail

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeProjectDetailRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="s1",
                input_tokens=10,
                output_tokens=5,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeProjectDetailRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="s2",
                input_tokens=20,
                output_tokens=7,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_project_detail(settings=settings, project_id="p1")

    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 12
    assert result.total_sessions == 2
    assert result.total_interactions == 7
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_project_detail_merges_local_sources_with_different_project_ids() -> None:
    from modelmeter.core.analytics import get_project_detail

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeProjectDetailRepo(
                project_id="opencode-p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="s1",
                input_tokens=10,
                output_tokens=5,
                total_interactions=3,
            ),
        ),
        (
            "local-claudecode",
            _FakeProjectDetailRepo(
                project_id="jsonl-hash-p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="s2",
                input_tokens=20,
                output_tokens=7,
                total_interactions=4,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_project_detail(settings=settings, project_id="opencode-p1")

    assert result.project_id == "opencode-p1"
    assert result.project_path == "/tmp/demo"
    assert result.usage.input_tokens == 30
    assert result.usage.output_tokens == 12
    assert result.total_sessions == 2
    assert result.total_interactions == 7
    assert {session.session_id for session in result.sessions} == {
        "local-opencode:s1",
        "local-claudecode:s2",
    }
    assert result.sources_considered == ["local-opencode", "local-claudecode"]
    assert result.sources_succeeded == ["local-opencode", "local-claudecode"]
    assert result.sources_failed == []


def test_get_project_detail_prices_providerless_model_ids() -> None:
    from modelmeter.core.analytics import get_project_detail

    settings = AppSettings()
    local_repos = [
        (
            "local-claudecode",
            _FakeProjectDetailRepo(
                project_id="jsonl-hash-p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="s2",
                model_id="claude-sonnet-4-6",
                provider_id="anthropic",
                input_tokens=20,
                output_tokens=7,
                total_interactions=4,
            ),
        ),
    ]

    pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}

    with (
        patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos),
        patch("modelmeter.core.analytics.load_pricing_book", return_value=(pricing_book, "test")),
    ):
        result = get_project_detail(settings=settings, project_id="jsonl-hash-p1")

    assert result.total_cost_usd is not None
    assert result.sessions[0].cost_usd is not None


def test_get_project_detail_merges_sessions_sorted_by_last_updated() -> None:
    from modelmeter.core.analytics import get_project_detail

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeProjectDetailRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="older-high-token",
                input_tokens=100,
                output_tokens=50,
                total_interactions=10,
                last_updated_ms=1000,
            ),
        ),
        (
            "local-claudecode",
            _FakeProjectDetailRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="newer-low-token",
                input_tokens=10,
                output_tokens=5,
                total_interactions=1,
                last_updated_ms=2000,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_project_detail(settings=settings, project_id="p1")

    assert [session.session_id for session in result.sessions] == [
        "local-claudecode:newer-low-token",
        "local-opencode:older-high-token",
    ]


def test_get_project_detail_merges_local_sources_with_collision_session_ids() -> None:
    from modelmeter.core.analytics import get_project_detail

    settings = AppSettings()
    local_repos = [
        (
            "local-opencode",
            _FakeProjectDetailRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="session-001",
                input_tokens=10,
                output_tokens=5,
                total_interactions=3,
                last_updated_ms=2000,
            ),
        ),
        (
            "local-claudecode",
            _FakeProjectDetailRepo(
                project_id="p1",
                project_name="demo",
                project_path="/tmp/demo",
                session_id="session-001",
                input_tokens=20,
                output_tokens=7,
                total_interactions=4,
                last_updated_ms=3000,
            ),
        ),
    ]

    with patch("modelmeter.core.analytics._resolve_local_repositories", return_value=local_repos):
        result = get_project_detail(settings=settings, project_id="p1")

    assert result.total_sessions == 2
    session_ids = {session.session_id for session in result.sessions}
    assert session_ids == {"local-opencode:session-001", "local-claudecode:session-001"}, (
        f"Expected namespaced session IDs, got {session_ids}"
    )
