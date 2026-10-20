"""FairHire Audit application."""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api import router
from app.db import session_scope
from app.errors import AppError
from app.services.maintenance import ensure_settings, reap_stale_runs
from app.services.seed import seed_if_empty
from app.settings import ROOT, enforce_bind, get_settings

log = logging.getLogger("fairhire")


def configure_logging() -> None:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(name)s %(message)s",
    )


def upgrade_database() -> None:
    from alembic import command
    from alembic.config import Config

    cfg = Config(str(ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(ROOT / "alembic"))
    cfg.set_main_option("sqlalchemy.url", get_settings().database_url)
    command.upgrade(cfg, "head")


def _ensure_sqlite_parent(url: str) -> None:
    if not url.startswith("sqlite:///"):
        return
    raw = url[len("sqlite:///") :]
    if raw == ":memory:":
        return
    Path(raw).parent.mkdir(parents=True, exist_ok=True)


@asynccontextmanager
async def lifespan(_app: FastAPI):
    configure_logging()
    settings = get_settings()
    enforce_bind(settings)
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.report_dir).mkdir(parents=True, exist_ok=True)
    _ensure_sqlite_parent(settings.database_url)
    upgrade_database()
    with session_scope() as session:
        ensure_settings(session)
        reap_stale_runs(session, stale_seconds=settings.stale_run_seconds)
        if settings.seed_demo and settings.app_env == "demo":
            seed_if_empty(session)
    yield


def create_app() -> FastAPI:
    settings = get_settings()
    app = FastAPI(title="FairHire Audit", version="0.1.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(router)

    @app.exception_handler(AppError)
    async def _app_error(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": exc.code, "detail": exc.message, "fields": exc.fields},
        )

    @app.exception_handler(RequestValidationError)
    async def _bad_body(_request: Request, _exc: RequestValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=422,
            content={
                "error": "invalid_body",
                "detail": "The request body is invalid.",
                "fields": {},
            },
        )

    @app.exception_handler(Exception)
    async def _unhandled(_request: Request, exc: Exception) -> JSONResponse:
        if isinstance(exc, HTTPException):
            return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})
        log.error("unhandled %s", type(exc).__name__)
        return JSONResponse(
            status_code=500,
            content={"error": "internal_error", "detail": "The request failed.", "fields": {}},
        )

    return app


app = create_app()
