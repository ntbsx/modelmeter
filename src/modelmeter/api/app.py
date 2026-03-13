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
from fastapi.responses import HTMLResponse, RedirectResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles

from modelmeter.config.settings import AppSettings
from modelmeter.core.analytics import (
    get_daily,
    get_model_detail,
    get_models,
    get_projects,
    get_summary,
)
from modelmeter.core.doctor import DoctorReport, generate_doctor_report
from modelmeter.core.live import get_live_snapshot
from modelmeter.core.models import (
    DailyResponse,
    LiveSnapshotResponse,
    ModelDetailResponse,
    ModelsResponse,
    ProjectsResponse,
    SummaryResponse,
)

LOCAL_CORS_ORIGINS = [
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://localhost:5173",
    "http://127.0.0.1:5173",
]

AUTH_EXEMPT_PATHS = {
    "/health",
}


def _optional_path(value: str | None) -> Path | None:
    if value is None:
        return None
    return Path(value)


def _raise_http_error(exc: RuntimeError) -> NoReturn:
    message = str(exc)
    if message.startswith("No data found for model"):
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
        if not auth_enabled or request.url.path in AUTH_EXEMPT_PATHS:
            return await call_next(request)

        decoded = _decode_basic_auth_header(request.headers.get("Authorization"))
        is_authorized = False
        if decoded is not None:
            username, password = decoded
            is_authorized = secrets.compare_digest(
                username, expected_username
            ) and secrets.compare_digest(password, expected_password)

        if not is_authorized:
            return Response(
                status_code=401,
                headers={"WWW-Authenticate": 'Basic realm="ModelMeter"'},
            )

        return await call_next(request)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

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

    @app.get("/api/summary", response_model=SummaryResponse)
    def summary(
        days: int | None = Query(default=7, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        session_source: Literal["auto", "activity", "session"] = Query(default="auto"),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> SummaryResponse:
        try:
            return get_summary(
                settings=settings,
                days=days,
                token_source=token_source,
                session_count_source=session_source,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
            )
        except RuntimeError as exc:
            _raise_http_error(exc)

    @app.get("/api/daily", response_model=DailyResponse)
    def daily(
        days: int | None = Query(default=7, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        session_source: Literal["auto", "activity", "session"] = Query(default="auto"),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> DailyResponse:
        try:
            return get_daily(
                settings=settings,
                days=days,
                token_source=token_source,
                session_count_source=session_source,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
            )
        except RuntimeError as exc:
            _raise_http_error(exc)

    @app.get("/api/models", response_model=ModelsResponse)
    def models(
        days: int | None = Query(default=7, ge=1),
        limit: int = Query(default=20, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> ModelsResponse:
        try:
            return get_models(
                settings=settings,
                days=days,
                limit=limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
            )
        except RuntimeError as exc:
            _raise_http_error(exc)

    @app.get("/api/models/{model_id:path}", response_model=ModelDetailResponse)
    def model_detail(
        model_id: str,
        days: int | None = Query(default=7, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> ModelDetailResponse:
        try:
            return get_model_detail(
                settings=settings,
                model_id=model_id,
                days=days,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
            )
        except RuntimeError as exc:
            _raise_http_error(exc)

    @app.get("/api/projects", response_model=ProjectsResponse)
    def projects(
        days: int | None = Query(default=7, ge=1),
        limit: int = Query(default=20, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> ProjectsResponse:
        try:
            return get_projects(
                settings=settings,
                days=days,
                limit=limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
            )
        except RuntimeError as exc:
            _raise_http_error(exc)

    @app.get("/api/live/snapshot", response_model=LiveSnapshotResponse)
    def live_snapshot(
        window_minutes: int = Query(default=60, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        models_limit: int = Query(default=5, ge=1),
        tools_limit: int = Query(default=8, ge=1),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> LiveSnapshotResponse:
        try:
            return get_live_snapshot(
                settings=settings,
                window_minutes=window_minutes,
                token_source=token_source,
                models_limit=models_limit,
                tools_limit=tools_limit,
                db_path_override=_optional_path(db_path),
                pricing_file_override=_optional_path(pricing_file),
            )
        except RuntimeError as exc:
            _raise_http_error(exc)

    @app.get("/api/live/events")
    async def live_events(
        window_minutes: int = Query(default=60, ge=1),
        token_source: Literal["auto", "message", "steps"] = Query(default="auto"),
        models_limit: int = Query(default=5, ge=1),
        tools_limit: int = Query(default=8, ge=1),
        interval_seconds: float = Query(default=3.0, ge=1.0, le=30.0),
        once: bool = Query(default=False),
        db_path: str | None = Query(default=None),
        pricing_file: str | None = Query(default=None),
    ) -> StreamingResponse:
        async def event_generator():
            while True:
                try:
                    snapshot = get_live_snapshot(
                        settings=settings,
                        window_minutes=window_minutes,
                        token_source=token_source,
                        models_limit=models_limit,
                        tools_limit=tools_limit,
                        db_path_override=_optional_path(db_path),
                        pricing_file_override=_optional_path(pricing_file),
                    )
                    payload = json.dumps(snapshot.model_dump(mode="json"))
                    yield f"event: live.snapshot\ndata: {payload}\n\n"
                except RuntimeError as exc:
                    payload = json.dumps({"detail": str(exc)})
                    yield f"event: live.error\ndata: {payload}\n\n"

                if once:
                    break

                await asyncio.sleep(interval_seconds)

        return StreamingResponse(
            event_generator(),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
            },
        )

    # Mount built React app if available
    web_dist = Path(__file__).parent.parent.parent.parent / "web" / "dist"
    if web_dist.exists():
        app.mount("/assets", StaticFiles(directory=web_dist / "assets"), name="assets")

        @app.get("/{full_path:path}")
        async def serve_spa(full_path: str):
            index_path = web_dist / "index.html"
            if index_path.exists():
                return HTMLResponse(index_path.read_text())
            return HTMLResponse(
                "UI build not found. Run 'npm run build' in web/ directory.", status_code=404
            )

    return app


app = create_app()
