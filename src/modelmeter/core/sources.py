"""Source registry and health checks for multi-source analytics."""

from __future__ import annotations

import base64
import json
import sqlite3
import urllib.error
import urllib.request
from pathlib import Path
from typing import Literal, cast

from pydantic import BaseModel, Field, model_validator

from modelmeter.config.settings import AppSettings


class SourceAuth(BaseModel):
    """Optional basic auth credentials for HTTP sources."""

    username: str
    password: str


class DataSourceConfig(BaseModel):
    """Single configured analytics source."""

    source_id: str = Field(min_length=1, max_length=64)
    label: str | None = None
    kind: Literal["sqlite", "http"]
    enabled: bool = True
    db_path: Path | None = None
    base_url: str | None = None
    auth: SourceAuth | None = None

    @model_validator(mode="after")
    def validate_kind_fields(self) -> DataSourceConfig:
        if self.kind == "sqlite":
            if self.db_path is None:
                raise ValueError("sqlite source requires db_path")
        elif self.base_url is None:
            raise ValueError("http source requires base_url")
        return self


class SourceRegistry(BaseModel):
    """Registry file payload for configured sources."""

    version: int = 1
    sources: list[DataSourceConfig] = Field(
        default_factory=lambda: cast(list[DataSourceConfig], [])
    )


class DataSourcePublic(BaseModel):
    """Public view of a source config with credentials redacted."""

    source_id: str
    label: str | None = None
    kind: Literal["sqlite", "http"]
    enabled: bool = True
    db_path: Path | None = None
    base_url: str | None = None
    has_auth: bool = False


class SourceRegistryPublic(BaseModel):
    """Public registry view with credentials stripped."""

    version: int = 1
    sources: list[DataSourcePublic] = Field(
        default_factory=lambda: cast(list[DataSourcePublic], [])
    )


class SourceHealth(BaseModel):
    """Health status for one source."""

    source_id: str
    kind: Literal["sqlite", "http"]
    is_reachable: bool
    detail: str | None = None
    error: str | None = None


def load_source_registry(*, settings: AppSettings) -> SourceRegistry:
    """Load source registry from configured path."""
    path = settings.source_registry_file
    if not path.exists():
        return SourceRegistry()

    try:
        payload = json.loads(path.read_text())
    except (OSError, ValueError):
        return SourceRegistry()

    if not isinstance(payload, dict):
        return SourceRegistry()
    return SourceRegistry.model_validate(payload)


def save_source_registry(*, settings: AppSettings, registry: SourceRegistry) -> None:
    """Persist source registry to configured path."""
    path = settings.source_registry_file
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(registry.model_dump_json(indent=2))


def upsert_source(*, settings: AppSettings, source: DataSourceConfig) -> None:
    """Create or replace one source in the registry."""
    registry = load_source_registry(settings=settings)
    filtered_sources = [entry for entry in registry.sources if entry.source_id != source.source_id]
    filtered_sources.append(source)
    save_source_registry(
        settings=settings,
        registry=SourceRegistry(version=registry.version, sources=filtered_sources),
    )


def remove_source(*, settings: AppSettings, source_id: str) -> bool:
    """Remove one source from the registry; return whether it existed."""
    registry = load_source_registry(settings=settings)
    filtered_sources = [entry for entry in registry.sources if entry.source_id != source_id]
    existed = len(filtered_sources) != len(registry.sources)
    if not existed:
        return False

    save_source_registry(
        settings=settings,
        registry=SourceRegistry(version=registry.version, sources=filtered_sources),
    )
    return True


def _check_sqlite_source(source: DataSourceConfig) -> SourceHealth:
    assert source.db_path is not None
    if not source.db_path.exists():
        return SourceHealth(
            source_id=source.source_id,
            kind=source.kind,
            is_reachable=False,
            error=f"DB not found at {source.db_path}",
        )

    uri = f"file:{source.db_path}?mode=ro"
    try:
        with sqlite3.connect(uri, uri=True) as conn:
            row = conn.execute("SELECT sqlite_version() AS version").fetchone()
    except sqlite3.Error as exc:
        return SourceHealth(
            source_id=source.source_id,
            kind=source.kind,
            is_reachable=False,
            error=str(exc),
        )

    version = str(row[0]) if row is not None else "unknown"
    return SourceHealth(
        source_id=source.source_id,
        kind=source.kind,
        is_reachable=True,
        detail=f"sqlite {version}",
    )


def _check_http_source(source: DataSourceConfig, *, timeout_seconds: int) -> SourceHealth:
    assert source.base_url is not None
    health_url = source.base_url.rstrip("/") + "/health"
    request = urllib.request.Request(health_url, headers={"User-Agent": "modelmeter/health-check"})

    if source.auth is not None:
        token_raw = f"{source.auth.username}:{source.auth.password}".encode()
        token = base64.b64encode(token_raw).decode("ascii")
        request.add_header("Authorization", f"Basic {token}")

    try:
        with urllib.request.urlopen(request, timeout=timeout_seconds) as response:
            status_code = int(getattr(response, "status", 200))
    except urllib.error.URLError as exc:
        return SourceHealth(
            source_id=source.source_id,
            kind=source.kind,
            is_reachable=False,
            error=str(exc.reason),
        )

    return SourceHealth(
        source_id=source.source_id,
        kind=source.kind,
        is_reachable=status_code == 200,
        detail=f"HTTP {status_code}",
        error=None if status_code == 200 else f"Unexpected status {status_code}",
    )


def to_public_registry(registry: SourceRegistry) -> SourceRegistryPublic:
    """Strip credentials from a registry for API responses."""
    public_sources = [
        DataSourcePublic(
            source_id=source.source_id,
            label=source.label,
            kind=source.kind,
            enabled=source.enabled,
            db_path=source.db_path,
            base_url=source.base_url,
            has_auth=source.auth is not None,
        )
        for source in registry.sources
    ]
    return SourceRegistryPublic(version=registry.version, sources=public_sources)


def check_source_health(*, source: DataSourceConfig, settings: AppSettings) -> SourceHealth:
    """Run reachability checks for one source."""
    if source.kind == "sqlite":
        return _check_sqlite_source(source)
    return _check_http_source(source, timeout_seconds=settings.source_http_timeout_seconds)
