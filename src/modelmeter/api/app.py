"""FastAPI application scaffold for ModelMeter."""

from __future__ import annotations

import asyncio
import base64
import binascii
import json
import secrets
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Literal, NoReturn

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import (
    FileResponse,
    HTMLResponse,
    RedirectResponse,
    Response,
    StreamingResponse,
)
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ValidationError

from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import (
    get_daily,
    get_model_detail,
    get_models,
    get_project_detail,
    get_projects,
    get_providers,
    get_summary,
)
from modelmeter.core.doctor import DoctorReport, generate_doctor_report
from modelmeter.core.live import get_live_snapshot
from modelmeter.core.models import (
    DailyResponse,
    LiveSnapshotResponse,
    ModelDetailResponse,
    ModelsResponse,
    ProjectDetailResponse,
    ProjectsResponse,
    ProvidersResponse,
    SummaryResponse,
    UpdateCheckResponse,
)
from modelmeter.core.sources import (
    DataSourceConfig,
    SourceAuth,
    SourceHealth,
    SourceRegistryError,
    SourceRegistryPublic,
    SourceScope,
    check_source_health,
    load_source_registry,
    remove_source,
    to_public_registry,
    upsert_source,
)
from modelmeter.core.updater import check_for_updates

LOCAL_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

AUTH_PROTECTED_PREFIXES = ("/api",)
SSE_PATH_PREFIXES = ("/api/live/events",)


class SourceUpsertRequest(BaseModel):
    label: str | None = None
    kind: Literal["sqlite", "http"]
    enabled: bool = True
    db_path: str | None = None
    base_url: str | None = None
    auth: SourceAuth | None = None
    preserve_existing_auth: bool = True


class SourceRemoveResponse(BaseModel):
    removed: bool


def _optional_path(value: str | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def _raise_http_error(exc: RuntimeError) -> NoReturn:
    message = str(exc)
    if message.startswith("No data found for model"):
        raise HTTPException(status_code=404, detail=message)
    if message.startswith("No data found for project"):
        raise HTTPException(status_code=404, detail=message)
    if "SQLite data source is unavailable or incompatible" in message:
        raise HTTPException(status_code=503, detail=message)
    raise HTTPException(status_code=500, detail=message)


def _decode_basic_auth_header(value: str | None) -> tuple[str, str] | None:
    if value is None or not value.startswith("Basic "):
        return None

    token = value[6:]
    try:
        decoded = base64.b64decode(token).decode("utf-8")
    except (binascii.Error, UnicodeDecodeError):
        return None

    if ":" not in decoded:
        return None

    username, password = decoded.split(":", 1)
    return username, password


def create_app(
    *,
    extra_cors_origins: list[str] | None = None,
    server_username: str | None = None,
    server_password: str | None = None,
) -> FastAPI:
    """Build and return the FastAPI app instance."""
    settings = AppSettings()
    app = FastAPI(title="ModelMeter", version=settings.app_version)

    cors_origins = [*LOCAL_CORS_ORIGINS]
    if extra_cors_origins:
        cors_origins.extend(extra_cors_origins)
    deduped_origins = list(dict.fromkeys(cors_origins))

    app.add_middleware(
        CORSMiddleware,
        allow_origins=deduped_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    auth_enabled = bool(server_password)
    expected_username = server_username or "modelmeter"
    expected_password = server_password or ""

    @app.middleware("http")
    async def maybe_require_basic_auth(
        request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        is_protected_path = request.url.path.startswith(AUTH_PROTECTED_PREFIXES)
        if not auth_enabled or not is_protected_path:
            return await call_next(request)

        decoded = _decode_basic_auth_header(request.headers.get("Authorization"))

        # Fallback: accept _auth query param (EventSource cannot set headers)
        if decoded is None:
            auth_param = request.query_params.get("_auth")
            if auth_param:
                decoded = _decode_basic_auth_header(f"Basic {auth_param}")

        is_authorized = False
        if decoded is not None:
            username, password = decoded
            is_authorized = secrets.compare_digest(
                username, expected_username
            ) and secrets.compare_digest(password, expected_password)

        if not is_authorized:
            is_sse_path = request.url.path.startswith(SSE_PATH_PREFIXES)
            headers = {} if is_sse_path else {"WWW-Authenticate": 'Basic realm="ModelMeter"'}
            return Response(
                content=json.dumps({"detail": "Invalid credentials"}),
                status_code=401,
                media_type="application/json",
                headers=headers,
            )

        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str | bool]:
        return {
            "status": "ok",
            "app_version": settings.app_runtime_version,
            "auth_required": auth_enabled,
        }

    @app.get("/doc", include_in_schema=False)
    def doc_alias() -> RedirectResponse:
        return RedirectResponse(url="/docs")

    @app.get("/api/doctor", response_model=DoctorReport)
    def doctor(
        db_path: str | None = Query(default=None),
    ) -> DoctorReport:
        return generate_doctor_report(
            settings=settings,
            db_path_override=_optional_path(db_path),
        )

    @app.get("/api/sources", response_model=SourceRegistryPublic)
    def sources() -> SourceRegistryPublic:
        try:
            registry = load_source_registry(settings=settings)
            return to_public_registry(registry)
        except SourceRegistryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.get("/api/sources/check", response_model=list[SourceHealth])
    def sources_check() -> list[SourceHealth]:
        try:
            registry = load_source_registry(settings=settings)
            return [
                check_source_health(source=source, settings=settings) for source in registry.sources
            ]
        except SourceRegistryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

    @app.put("/api/sources/{source_id}", response_model=SourceRegistryPublic)
    def upsert_source_api(source_id: str, payload: SourceUpsertRequest) -> SourceRegistryPublic:
        try:
            registry = load_source_registry(settings=settings)
            existing = next(
                (item for item in registry.sources if item.source_id == source_id), None
            )

            auth = payload.auth
            if (
                payload.kind == "http"
                and auth is None
                and payload.preserve_existing_auth
                and existing is not None
                and existing.kind == "http"
            ):
                auth = existing.auth

            source = DataSourceConfig(
                source_id=source_id,
                label=payload.label,
                kind=payload.kind,
                enabled=payload.enabled,
                db_path=_optional_path(payload.db_path),
                base_url=payload.base_url,
                auth=auth,
            )
            upsert_source(settings=settings, source=source)
            updated = load_source_registry(settings=settings)
            return to_public_registry(updated)
        except SourceRegistryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc
        except (ValidationError, ValueError) as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.delete("/api/sources/{source_id}", response_model=SourceRemoveResponse)
    def remove_source_api(source_id: str) -> SourceRemoveResponse:
        try:
            removed = remove_source(settings=settings, source_id=source_id)
        except SourceRegistryError as exc:
            raise HTTPException(status_code=500, detail=str(exc)) from exc

        if not removed:
            raise HTTPException(status_code=404, detail=f"No source found with id '{source_id}'.")

        return SourceRemoveResponse(removed=True)

    @app.get("/api/auth/check")
    def auth_check() -> dict[str, str]:
        return {
            "status": "ok",
            "app_version": settings.app_runtime_version,
        }

    @app.get("/api/update/check", response_model=UpdateCheckResponse)
    def update_check() -> UpdateCheckResponse:
        return check_for_updates(settings=settings)

    @app.get("/api/summary", response_model=SummaryResponse)
    def summary(
        days: int | None = Query(default=7, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        session_source: Literal["auto", "activity", "session"] = Query(default="auto"),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> SummaryResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_summary(
                settings=settings,
                days=days,
                token_source=token_source,
                session_count_source=session_source,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/daily", response_model=DailyResponse)
    def daily(
        days: int | None = Query(default=7, ge=1),
        timezone_offset_minutes: int = Query(default=0, ge=-840, le=840),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        session_source: Literal["auto", "activity", "session"] = Query(default="auto"),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> DailyResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_daily(
                settings=settings,
                days=days,
                timezone_offset_minutes=timezone_offset_minutes,
                token_source=token_source,
                session_count_source=session_source,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/models", response_model=ModelsResponse)
    def models(
        days: int | None = Query(default=7, ge=1),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=20, ge=1),
        provider: str | None = Query(default=None),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> ModelsResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_models(
                settings=settings,
                days=days,
                offset=offset,
                limit=limit,
                provider=provider,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/providers", response_model=ProvidersResponse)
    def providers(
        days: int | None = Query(default=7, ge=1),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=20, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> ProvidersResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_providers(
                settings=settings,
                days=days,
                offset=offset,
                limit=limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/models/{model_id:path}", response_model=ModelDetailResponse)
    def model_detail(
        model_id: str,
        days: int | None = Query(default=7, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> ModelDetailResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_model_detail(
                settings=settings,
                model_id=model_id,
                days=days,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects", response_model=ProjectsResponse)
    def projects(
        days: int | None = Query(default=7, ge=1),
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=20, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> ProjectsResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_projects(
                settings=settings,
                days=days,
                offset=offset,
                limit=limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/projects/{project_id}", response_model=ProjectDetailResponse)
    def project_detail(
        project_id: str,
        days: int | None = Query(default=None, ge=1),
        session_offset: int = Query(default=0, ge=0),
        session_limit: int | None = Query(default=None, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> ProjectDetailResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_project_detail(
                settings=settings,
                project_id=project_id,
                days=days,
                session_offset=session_offset,
                session_limit=session_limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/live/snapshot", response_model=LiveSnapshotResponse)
    def live_snapshot(
        window_minutes: int = Query(default=60, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        models_limit: int = Query(default=5, ge=1),
        tools_limit: int = Query(default=8, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> LiveSnapshotResponse:
        try:
            scope = SourceScope.parse(source_scope) if source_scope is not None else None
            return get_live_snapshot(
                settings=settings,
                window_minutes=window_minutes,
                token_source=token_source,
                models_limit=models_limit,
                tools_limit=tools_limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
                source_scope=scope,
            )
        except NotImplementedError as exc:
            raise HTTPException(status_code=501, detail=str(exc)) from exc
        except RuntimeError as exc:
            _raise_http_error(exc)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc

    @app.get("/api/live/events")
    async def live_events(
        request: Request,
        window_minutes: int = Query(default=60, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        models_limit: int = Query(default=5, ge=1),
        tools_limit: int = Query(default=8, ge=1),
        interval_seconds: float = Query(default=3.0, ge=1.0, le=30.0),
        once: bool = Query(default=False),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
        source_scope: str | None = Query(
            default=None, description="Source scope: local, all, or source:<id>"
        ),
    ) -> StreamingResponse:
        async def event_generator():
            try:
                while True:
                    if await request.is_disconnected():
                        break

                    try:
                        scope = (
                            SourceScope.parse(source_scope) if source_scope is not None else None
                        )
                        snapshot = get_live_snapshot(
                            settings=settings,
                            window_minutes=window_minutes,
                            token_source=token_source,
                            models_limit=models_limit,
                            tools_limit=tools_limit,
                            db_path_override=_optional_path(db_path),
                            pricing_file_override=_optional_path(pricing_file),
                            source_scope=scope,
                        )
                        payload = json.dumps(snapshot.model_dump(mode="json"))
                        yield f"event: live.snapshot\ndata: {payload}\n\n"
                    except (NotImplementedError, ValueError) as exc:
                        payload = json.dumps({"detail": str(exc)})
                        yield f"event: live.error\ndata: {payload}\n\n"
                        if once:
                            break
                        await asyncio.sleep(interval_seconds)
                        continue
                    except RuntimeError as exc:
                        payload = json.dumps({"detail": str(exc)})
                        yield f"event: live.error\ndata: {payload}\n\n"

                    if once:
                        break

                    await asyncio.sleep(interval_seconds)
            except asyncio.CancelledError:
                return

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # Mount built React app if available.
    # Prefer local repo build for development.
    # Fall back to packaged assets for installed wheels.
    packaged_web_dist = Path(__file__).resolve().parent.parent / "web_dist"
    local_web_dist = Path(__file__).resolve().parent.parent.parent.parent / "web" / "dist"

    web_dist = local_web_dist if local_web_dist.exists() else packaged_web_dist
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/favicon.svg", include_in_schema=False)
        async def serve_favicon() -> FileResponse:
            favicon_path = web_dist / "favicon.svg"
            if not favicon_path.exists():
                raise HTTPException(status_code=404, detail="Favicon not found")
            return FileResponse(favicon_path, media_type="image/svg+xml")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_spa(full_path: str):
            index_path = web_dist / "index.html"
            if index_path.exists():
                return HTMLResponse(index_path.read_text())
            return HTMLResponse(
                "UI build not found. Run 'npm run --prefix web build' and package assets.",
                status_code=404,
            )

    return app


app = create_app()
