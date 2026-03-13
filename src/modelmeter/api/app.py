"""FastAPI application scaffold for ModelMeter."""

from __future__ import annotations

from pathlib import Path
from typing import Literal, NoReturn

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware

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


def create_app() -> FastAPI:
    """Build and return the FastAPI app instance."""
    settings = AppSettings()
    app = FastAPI(title="ModelMeter", version=settings.app_version)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=LOCAL_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/doctor", response_model=DoctorReport)
    def doctor(
        db_path: str | None = Query(default=None),
    ) -> DoctorReport:
        return generate_doctor_report(
            settings=settings,
            db_path_override=_optional_path(db_path),
        )

    @app.get("/summary", response_model=SummaryResponse)
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

    @app.get("/daily", response_model=DailyResponse)
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

    @app.get("/models", response_model=ModelsResponse)
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

    @app.get("/models/{model_id}", response_model=ModelDetailResponse)
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

    @app.get("/projects", response_model=ProjectsResponse)
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

    @app.get("/live/snapshot", response_model=LiveSnapshotResponse)
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

    return app


app = create_app()
