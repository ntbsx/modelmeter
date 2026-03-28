from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import (
    _canonical_project_id,
    get_daily,
    get_models,
    get_projects,
    get_providers,
    get_summary,
)
from modelmeter.core.federation import (
    merge_model_usage,
    merge_project_usage,
    merge_provider_usage,
    merge_token_usage,
)
from modelmeter.core.models import (
    ModelUsage,
    ProjectUsage,
    ProviderUsage,
    TokenUsage,
)
from modelmeter.core.pricing import ModelPricing
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceAuth,
    SourceRegistry,
    SourceScope,
    SourceScopeKind,
    get_sources_for_scope,
    load_source_registry,
    save_source_registry,
)


def _patch_local_sqlite_path(
    monkeypatch: pytest.MonkeyPatch,
    *,
    path: Path,
) -> None:
    def _fake_resolve(_settings: AppSettings, db_path_override: Path | None = None) -> Path:
        return db_path_override or path

    monkeypatch.setattr("modelmeter.core.analytics._resolve_sqlite_path", _fake_resolve)


def _create_simple_usage_fixture(db_path: Path, model_prefix: str = "claude") -> None:
    """Create a simple usage fixture with known token counts."""
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
            "INSERT INTO project (id, worktree, name) VALUES (?, ?, ?)",
            ("p1", "/tmp/project-one", "project-one"),
        )

        assistant_msg = {
            "role": "assistant",
            "modelID": f"anthropic/{model_prefix}",
            "time": {"created": now_ms},
            "tokens": {
                "input": 100,
                "output": 50,
                "cache": {"read": 20, "write": 10},
            },
        }

        conn.execute(
            "INSERT INTO message (id, session_id, data) VALUES (?, ?, ?)",
            ("m1", "s1", json.dumps(assistant_msg)),
        )


class TestMergeFunctions:
    """Test merge helper functions."""

    def testmerge_token_usage_sums_fields(self) -> None:
        a = TokenUsage(
            input_tokens=100, output_tokens=50, cache_read_tokens=20, cache_write_tokens=10
        )
        b = TokenUsage(
            input_tokens=200, output_tokens=30, cache_read_tokens=5, cache_write_tokens=5
        )
        result = merge_token_usage(a, b)
        assert result.input_tokens == 300
        assert result.output_tokens == 80
        assert result.cache_read_tokens == 25
        assert result.cache_write_tokens == 15

    def testmerge_model_usage_sums_fields(self) -> None:
        a = ModelUsage(
            model_id="test-model",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            total_sessions=10,
            total_interactions=100,
            cost_usd=1.0,
            has_pricing=True,
        )
        b = ModelUsage(
            model_id="test-model",
            usage=TokenUsage(input_tokens=200, output_tokens=30),
            total_sessions=5,
            total_interactions=50,
            cost_usd=0.5,
            has_pricing=False,
        )
        result = merge_model_usage(a, b)
        assert result.model_id == "test-model"
        assert result.usage.input_tokens == 300
        assert result.usage.output_tokens == 80
        assert result.total_sessions == 15
        assert result.total_interactions == 150
        assert result.cost_usd == 1.5
        assert result.has_pricing is True

    def testmerge_provider_usage_sums_fields(self) -> None:
        a = ProviderUsage(
            provider="anthropic",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            total_models=5,
            total_interactions=100,
            cost_usd=1.0,
            has_pricing=True,
        )
        b = ProviderUsage(
            provider="anthropic",
            usage=TokenUsage(input_tokens=200, output_tokens=30),
            total_models=3,
            total_interactions=50,
            cost_usd=0.5,
            has_pricing=False,
        )
        result = merge_provider_usage(a, b)
        assert result.provider == "anthropic"
        assert result.usage.input_tokens == 300
        assert result.usage.output_tokens == 80
        assert result.total_models == 8
        assert result.total_interactions == 150
        assert result.cost_usd == 1.5
        assert result.has_pricing is True

    def test_merge_project_usage_sums_fields(self) -> None:
        a = ProjectUsage(
            project_id="p1",
            project_name="Project One",
            project_path="/tmp/project-one",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            total_sessions=10,
            total_interactions=100,
            cost_usd=1.0,
            has_pricing=True,
            sources=["local"],
        )
        b = ProjectUsage(
            project_id="p1",
            project_name="Project One",
            project_path="/tmp/project-one",
            usage=TokenUsage(input_tokens=200, output_tokens=30),
            total_sessions=5,
            total_interactions=50,
            cost_usd=0.5,
            has_pricing=False,
            sources=["remote-prod"],
        )
        result = merge_project_usage(a, b)
        assert result.project_id == "p1"
        assert result.project_name == "Project One"
        assert result.usage.input_tokens == 300
        assert result.usage.output_tokens == 80
        assert result.total_sessions == 15
        assert result.total_interactions == 150
        assert result.cost_usd == 1.5
        assert result.has_pricing is True
        assert set(result.sources) == {"local", "remote-prod"}

    def test_merge_project_usage_combines_multiple_sources(self) -> None:
        a = ProjectUsage(
            project_id="p1",
            project_name="Project One",
            usage=TokenUsage(input_tokens=100, output_tokens=50),
            total_sessions=10,
            total_interactions=100,
            sources=["local", "remote-a"],
        )
        b = ProjectUsage(
            project_id="p1",
            project_name="Project One",
            usage=TokenUsage(input_tokens=200, output_tokens=30),
            total_sessions=5,
            total_interactions=50,
            sources=["remote-b"],
        )
        c = ProjectUsage(
            project_id="p1",
            project_name="Project One",
            usage=TokenUsage(input_tokens=50, output_tokens=10),
            total_sessions=2,
            total_interactions=20,
            sources=["local"],
        )
        result = merge_project_usage(merge_project_usage(a, b), c)
        assert set(result.sources) == {"local", "remote-a", "remote-b"}


class TestSourceScope:
    """Test SourceScope parsing and selection."""

    def test_parse_local_scope(self) -> None:
        scope = SourceScope.parse("local")
        assert scope.kind == SourceScopeKind.LOCAL
        assert scope.source_id is None

    def test_parse_all_scope(self) -> None:
        scope = SourceScope.parse("all")
        assert scope.kind == SourceScopeKind.ALL
        assert scope.source_id is None

    def test_parse_specific_scope(self) -> None:
        scope = SourceScope.parse("source:my-id")
        assert scope.kind == SourceScopeKind.SPECIFIC
        assert scope.source_id == "my-id"

    def test_parse_none_returns_local(self) -> None:
        scope = SourceScope.parse(None)
        assert scope.kind == SourceScopeKind.LOCAL


class TestFederatedQueries:
    """Test federated queries across multiple sources."""

    def test_federated_jsonl_scope_preserves_cache_tokens(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        class _FakeJsonlRepo:
            def fetch_summary(self, *, days: int | None = None) -> dict[str, int]:
                _ = days
                return {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_read": 20,
                    "cache_write": 10,
                    "total_sessions": 1,
                }

            def fetch_summary_steps(self, *, days: int | None = None) -> dict[str, int]:
                return self.fetch_summary(days=days)

            def fetch_session_count(self, *, days: int | None = None) -> int:
                _ = days
                return 1

            def resolve_token_source(
                self, *, days: int | None = None, token_source: str = "auto"
            ) -> str:
                _ = days
                return "message" if token_source == "auto" else token_source

            def resolve_session_count_source(
                self, *, days: int | None = None, session_count_source: str = "auto"
            ) -> str:
                _ = days
                return "session" if session_count_source == "auto" else session_count_source

            def fetch_daily(
                self, *, days: int | None = None, timezone_offset_minutes: int = 0
            ) -> list[dict[str, object]]:
                _ = (days, timezone_offset_minutes)
                return [
                    {
                        "day": "2026-03-27",
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read": 20,
                        "cache_write": 10,
                        "total_sessions": 1,
                    }
                ]

            def fetch_daily_steps(
                self, *, days: int | None = None, timezone_offset_minutes: int = 0
            ) -> list[dict[str, object]]:
                return self.fetch_daily(days=days, timezone_offset_minutes=timezone_offset_minutes)

            def fetch_model_usage(self, *, days: int | None = None) -> list[dict[str, object]]:
                return self.fetch_model_usage_detail(days=days)

            def fetch_model_usage_detail(
                self, *, days: int | None = None
            ) -> list[dict[str, object]]:
                _ = days
                return [
                    {
                        "model_id": "claude-sonnet-4-6",
                        "provider_id": "anthropic",
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read": 20,
                        "cache_write": 10,
                        "total_sessions": 1,
                        "total_interactions": 2,
                    }
                ]

            def fetch_project_usage_detail(
                self, *, days: int | None = None
            ) -> list[dict[str, object]]:
                _ = days
                return [
                    {
                        "project_id": "p1",
                        "project_name": "demo",
                        "project_path": "/tmp/demo",
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read": 20,
                        "cache_write": 10,
                        "total_sessions": 1,
                        "total_interactions": 2,
                    }
                ]

            def fetch_daily_model_usage(
                self, *, days: int | None = None, timezone_offset_minutes: int = 0
            ) -> list[dict[str, object]]:
                _ = (days, timezone_offset_minutes)
                return [
                    {
                        "day": "2026-03-27",
                        "model_id": "claude-sonnet-4-6",
                        "provider_id": "anthropic",
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read": 20,
                        "cache_write": 10,
                    }
                ]

            def fetch_project_model_usage(
                self, *, days: int | None = None
            ) -> list[dict[str, object]]:
                _ = days
                return [
                    {
                        "project_id": "p1",
                        "model_id": "claude-sonnet-4-6",
                        "provider_id": "anthropic",
                        "input_tokens": 100,
                        "output_tokens": 50,
                        "cache_read": 20,
                        "cache_write": 10,
                    }
                ]

        jsonl_dir = tmp_path / "jsonl"
        jsonl_dir.mkdir()
        (jsonl_dir / "session-001.jsonl").write_text("{}\n", encoding="utf-8")

        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path, claudecode_enabled=False)
        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="jsonl-source",
                    kind="jsonl",
                    db_path=jsonl_dir,
                    enabled=True,
                )
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        def _fake_create_repository(kind: str, path: Path) -> Any:
            _ = (kind, path)
            return _FakeJsonlRepo()

        monkeypatch.setattr("modelmeter.core.federation.create_repository", _fake_create_repository)

        pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}

        def _fake_load_pricing_book(
            settings: AppSettings, pricing_file_override: Path | None = None
        ) -> tuple[dict[str, ModelPricing], str]:
            _ = (settings, pricing_file_override)
            return pricing_book, "test-pricing"

        monkeypatch.setattr(
            "modelmeter.core.federation.load_pricing_book",
            _fake_load_pricing_book,
            raising=False,
        )

        scope = SourceScope(kind=SourceScopeKind.SPECIFIC, source_id="jsonl-source")

        summary = get_summary(settings=settings, days=7, source_scope=scope)
        daily = get_daily(settings=settings, days=7, source_scope=scope)
        models = get_models(settings=settings, days=7, source_scope=scope)
        providers = get_providers(settings=settings, days=7, source_scope=scope)
        projects = get_projects(settings=settings, days=7, source_scope=scope)

        expected_cost = 0.0010935

        assert summary.usage.cache_read_tokens == 20
        assert summary.usage.cache_write_tokens == 10
        assert summary.cost_usd == expected_cost
        assert summary.pricing_source == "test-pricing"
        assert daily.totals.cache_read_tokens == 20
        assert daily.totals.cache_write_tokens == 10
        assert daily.daily[0].usage.cache_read_tokens == 20
        assert daily.daily[0].usage.cache_write_tokens == 10
        assert daily.total_cost_usd == expected_cost
        assert daily.daily[0].cost_usd == expected_cost
        assert models.totals.cache_read_tokens == 20
        assert models.totals.cache_write_tokens == 10
        assert models.total_cost_usd == expected_cost
        assert models.pricing_source == "test-pricing"
        assert models.models[0].model_id == "anthropic/claude-sonnet-4-6"
        assert models.models[0].provider == "anthropic"
        assert models.models[0].cost_usd == expected_cost
        assert models.models[0].has_pricing is True
        assert models.models[0].usage.cache_read_tokens == 20
        assert models.models[0].usage.cache_write_tokens == 10
        assert providers.total_cost_usd == expected_cost
        assert providers.pricing_source == "test-pricing"
        assert providers.providers[0].provider == "anthropic"
        assert providers.providers[0].cost_usd == expected_cost
        assert providers.providers[0].has_pricing is True
        assert providers.providers[0].usage.cache_read_tokens == 20
        assert providers.providers[0].usage.cache_write_tokens == 10
        assert projects.total_cost_usd == expected_cost
        assert projects.pricing_source == "test-pricing"
        assert projects.projects[0].project_id == _canonical_project_id("p1", "/tmp/demo")
        assert projects.projects[0].cost_usd == expected_cost
        assert projects.projects[0].has_pricing is True
        assert projects.projects[0].usage.cache_read_tokens == 20
        assert projects.projects[0].usage.cache_write_tokens == 10

    def test_federated_jsonl_provider_deduplicates_duplicate_model_rows(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """JSONL source returning 2 rows with same model_id should report total_models=1."""

        class _FakeJsonlRepoWithDupes:
            def fetch_summary(self, *, days: int | None = None) -> dict[str, int]:
                _ = days
                return {
                    "input_tokens": 100,
                    "output_tokens": 50,
                    "cache_read": 20,
                    "cache_write": 10,
                    "total_sessions": 2,
                }

            def fetch_summary_steps(self, *, days: int | None = None) -> dict[str, int]:
                return self.fetch_summary(days=days)

            def fetch_session_count(self, *, days: int | None = None) -> int:
                _ = days
                return 2

            def resolve_token_source(
                self, *, days: int | None = None, token_source: str = "auto"
            ) -> str:
                _ = days
                return "message" if token_source == "auto" else token_source

            def resolve_session_count_source(
                self, *, days: int | None = None, session_count_source: str = "auto"
            ) -> str:
                _ = days
                return "session" if session_count_source == "auto" else session_count_source

            def fetch_model_usage_detail(
                self, *, days: int | None = None
            ) -> list[dict[str, object]]:
                _ = days
                return [
                    {
                        "model_id": "claude-sonnet-4-6",
                        "provider_id": "anthropic",
                        "input_tokens": 50,
                        "output_tokens": 25,
                        "cache_read": 10,
                        "cache_write": 5,
                        "total_sessions": 1,
                        "total_interactions": 1,
                    },
                    {
                        "model_id": "claude-sonnet-4-6",
                        "provider_id": "anthropic",
                        "input_tokens": 50,
                        "output_tokens": 25,
                        "cache_read": 10,
                        "cache_write": 5,
                        "total_sessions": 1,
                        "total_interactions": 1,
                    },
                ]

        jsonl_dir = tmp_path / "jsonl"
        jsonl_dir.mkdir()
        (jsonl_dir / "session-001.jsonl").write_text("{}\n", encoding="utf-8")

        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path, claudecode_enabled=False)
        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="jsonl-dupes",
                    kind="jsonl",
                    db_path=jsonl_dir,
                    enabled=True,
                )
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        def _fake_create_repository(kind: str, path: Path) -> Any:
            _ = (kind, path)
            return _FakeJsonlRepoWithDupes()

        monkeypatch.setattr("modelmeter.core.federation.create_repository", _fake_create_repository)

        def _fake_load_pricing_book(
            settings: AppSettings, pricing_file_override: Path | None = None
        ) -> tuple[dict[str, ModelPricing], str]:
            _ = (settings, pricing_file_override)
            pricing_book = {"anthropic/claude-sonnet-4-6": ModelPricing(3.0, 15.0, 0.3, 3.75)}
            return pricing_book, "test-pricing"

        monkeypatch.setattr(
            "modelmeter.core.federation.load_pricing_book",
            _fake_load_pricing_book,
            raising=False,
        )

        scope = SourceScope(kind=SourceScopeKind.SPECIFIC, source_id="jsonl-dupes")
        providers = get_providers(settings=settings, days=7, source_scope=scope)

        assert len(providers.providers) == 1
        assert providers.providers[0].provider == "anthropic"
        assert providers.providers[0].total_models == 1
        assert providers.providers[0].total_interactions == 1
        assert providers.total_sessions == 2

    def test_local_scope_returns_local_data(self, tmp_path: Path) -> None:
        """When source_scope=local with db_path_override, should return that db's data."""
        db_path = tmp_path / "test.db"
        _create_simple_usage_fixture(db_path)

        settings = AppSettings(
            source_registry_file=tmp_path / "sources.json",
        )

        result = get_summary(
            settings=settings,
            days=7,
            db_path_override=db_path,
            source_scope=SourceScope(kind=SourceScopeKind.LOCAL),
        )

        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50

    def test_federated_summary_specific_scope(self, tmp_path: Path) -> None:
        """When source_scope=source:<id>, should query only that source."""
        db1 = tmp_path / "db1.db"
        _create_simple_usage_fixture(db1, model_prefix="claude-1")

        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="source1",
                    kind="sqlite",
                    db_path=db1,
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        result = get_summary(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.SPECIFIC, source_id="source1"),
        )

        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50

    def test_federated_summary_merges_multiple_sources(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source_scope=all with sqlite sources, should merge local + federated data."""
        local_db = tmp_path / "local.db"
        db1 = tmp_path / "db1.db"
        db2 = tmp_path / "db2.db"
        _create_simple_usage_fixture(local_db, model_prefix="claude-local")
        _create_simple_usage_fixture(db1, model_prefix="claude-1")
        _create_simple_usage_fixture(db2, model_prefix="claude-2")

        _patch_local_sqlite_path(monkeypatch, path=local_db)

        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path, claudecode_enabled=False)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="source1",
                    kind="sqlite",
                    db_path=db1,
                    enabled=True,
                ),
                DataSourceConfig(
                    source_id="source2",
                    kind="sqlite",
                    db_path=db2,
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        result = get_summary(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.usage.input_tokens == 300
        assert result.usage.output_tokens == 150
        assert result.source_scope == "all"
        assert "local" in result.sources_considered
        assert "source1" in result.sources_considered
        assert "source2" in result.sources_considered
        assert len(result.sources_succeeded) == 3
        assert len(result.sources_failed) == 0

    def test_all_scope_with_no_sources_includes_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source_scope=all and no registry sources, should still include local."""
        local_db = tmp_path / "local.db"
        _create_simple_usage_fixture(local_db)

        _patch_local_sqlite_path(monkeypatch, path=local_db)

        settings = AppSettings(source_registry_file=tmp_path / "sources.json", claudecode_enabled=False)
        result = get_summary(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50
        assert result.source_scope == "all"
        assert result.sources_considered == ["local"]
        assert result.sources_succeeded == ["local"]
        assert result.sources_failed == []

    def test_all_scope_daily_includes_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source_scope=all, get_daily should include local totals."""
        local_db = tmp_path / "local.db"
        _create_simple_usage_fixture(local_db)

        _patch_local_sqlite_path(monkeypatch, path=local_db)

        settings = AppSettings(source_registry_file=tmp_path / "sources.json", claudecode_enabled=False)
        result = get_daily(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.source_scope == "all"
        assert result.totals.input_tokens == 100
        assert result.totals.output_tokens == 50
        assert "local" in result.sources_considered
        assert len(result.daily) > 0

    def test_all_scope_models_includes_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source_scope=all, get_models should include local totals."""
        local_db = tmp_path / "local.db"
        _create_simple_usage_fixture(local_db)

        _patch_local_sqlite_path(monkeypatch, path=local_db)

        settings = AppSettings(source_registry_file=tmp_path / "sources.json", claudecode_enabled=False)
        result = get_models(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.source_scope == "all"
        assert result.totals.input_tokens == 100
        assert result.totals.output_tokens == 50
        assert "local" in result.sources_considered
        assert result.total_models >= 1
        assert len(result.models) >= 1

    def test_all_scope_providers_includes_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source_scope=all, get_providers should include local totals."""
        local_db = tmp_path / "local.db"
        _create_simple_usage_fixture(local_db)

        _patch_local_sqlite_path(monkeypatch, path=local_db)

        settings = AppSettings(source_registry_file=tmp_path / "sources.json", claudecode_enabled=False)
        result = get_providers(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.source_scope == "all"
        assert result.totals.input_tokens == 100
        assert result.totals.output_tokens == 50
        assert "local" in result.sources_considered
        assert result.total_providers >= 1
        assert len(result.providers) >= 1

    def test_all_scope_projects_includes_local(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """When source_scope=all, get_projects should include local totals."""
        local_db = tmp_path / "local.db"
        _create_simple_usage_fixture(local_db)

        _patch_local_sqlite_path(monkeypatch, path=local_db)

        settings = AppSettings(source_registry_file=tmp_path / "sources.json", claudecode_enabled=False)
        result = get_projects(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.source_scope == "all"
        assert result.totals.input_tokens == 100
        assert result.totals.output_tokens == 50
        assert "local" in result.sources_considered
        assert result.total_projects >= 1
        assert len(result.projects) >= 1

    def test_all_scope_degrades_when_local_sqlite_unavailable(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """ALL scope should still work with remote sources even if local SQLite is unavailable."""
        db1 = tmp_path / "db1.db"
        _create_simple_usage_fixture(db1, model_prefix="claude-1")

        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path, claudecode_enabled=False)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="source1",
                    kind="sqlite",
                    db_path=db1,
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        def _raise_local_unavailable(
            _settings: AppSettings, db_path_override: Path | None = None
        ) -> Path:
            if db_path_override is not None:
                return db_path_override
            raise RuntimeError("SQLite data source is unavailable or incompatible")

        monkeypatch.setattr(
            "modelmeter.core.analytics._resolve_sqlite_path", _raise_local_unavailable
        )

        result = get_summary(
            settings=settings,
            days=7,
            source_scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert result.usage.input_tokens == 100
        assert result.usage.output_tokens == 50
        assert "source1" in result.sources_succeeded
        assert any(f["source_id"] == "local" for f in result.sources_failed)


class TestSourceRegistry:
    """Test source registry loading and saving."""

    def test_save_and_load_source_registry(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="local",
                    kind="sqlite",
                    db_path=Path("/tmp/test.db"),
                    enabled=True,
                ),
                DataSourceConfig(
                    source_id="remote",
                    kind="http",
                    base_url="https://example.com",
                    auth=SourceAuth(username="user", password="pass"),
                    enabled=True,
                ),
            ]
        )

        save_source_registry(settings=settings, registry=registry)

        loaded = load_source_registry(settings=settings)
        assert len(loaded.sources) == 2
        assert loaded.sources[0].source_id == "local"
        assert loaded.sources[1].source_id == "remote"
        assert loaded.sources[1].auth is not None

    def test_get_sources_for_scope_local(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="local",
                    kind="sqlite",
                    db_path=Path("/tmp/test.db"),
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        sources, failures = get_sources_for_scope(
            settings=settings,
            scope=SourceScope(kind=SourceScopeKind.LOCAL),
        )

        assert sources == []
        assert failures == []

    def test_get_sources_for_scope_all(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path)

        db1 = tmp_path / "db1.db"
        db2 = tmp_path / "db2.db"
        _create_simple_usage_fixture(db1, model_prefix="claude-1")
        _create_simple_usage_fixture(db2, model_prefix="claude-2")

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="source1",
                    kind="sqlite",
                    db_path=db1,
                    enabled=True,
                ),
                DataSourceConfig(
                    source_id="source2",
                    kind="sqlite",
                    db_path=db2,
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        sources, failures = get_sources_for_scope(
            settings=settings,
            scope=SourceScope(kind=SourceScopeKind.ALL),
        )

        assert len(sources) == 2
        assert failures == []

    def test_get_sources_for_scope_specific(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path)

        db1 = tmp_path / "db1.db"
        db2 = tmp_path / "db2.db"
        _create_simple_usage_fixture(db1)
        _create_simple_usage_fixture(db2)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="source1",
                    kind="sqlite",
                    db_path=db1,
                    enabled=True,
                ),
                DataSourceConfig(
                    source_id="source2",
                    kind="sqlite",
                    db_path=db2,
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        sources, failures = get_sources_for_scope(
            settings=settings,
            scope=SourceScope(kind=SourceScopeKind.SPECIFIC, source_id="source2"),
        )

        assert len(sources) == 1
        assert sources[0].source_id == "source2"
        assert failures == []

    def test_get_sources_for_scope_specific_unreachable(self, tmp_path: Path) -> None:
        registry_path = tmp_path / "sources.json"
        settings = AppSettings(source_registry_file=registry_path)

        registry = SourceRegistry(
            sources=[
                DataSourceConfig(
                    source_id="remote-unreachable",
                    kind="http",
                    base_url="http://127.0.0.1:1",
                    enabled=True,
                ),
            ]
        )
        save_source_registry(settings=settings, registry=registry)

        sources, failures = get_sources_for_scope(
            settings=settings,
            scope=SourceScope(kind=SourceScopeKind.SPECIFIC, source_id="remote-unreachable"),
        )

        assert sources == []
        assert len(failures) == 1
        assert failures[0].source_id == "remote-unreachable"
        assert failures[0].kind == "http"
