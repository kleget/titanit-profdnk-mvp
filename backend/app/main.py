from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import Base, engine, SessionLocal
from app.routers import admin, api, auth, psychologist, public
from app.services.seed import seed_initial_data


def create_app() -> FastAPI:
    app = FastAPI(
        title="ПрофДНК API",
        description="Минимальная версия платформы ПрофДНК для хакатона ТИТАНИТ",
        version="0.1.0",
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        session_cookie="profdnk_session",
        same_site=settings.session_same_site,
        https_only=settings.session_https_only,
        max_age=60 * 60 * 24 * 7,
    )

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(psychologist.router)
    app.include_router(public.router)
    app.include_router(api.router)

    @app.on_event("startup")
    def on_startup() -> None:
        Base.metadata.create_all(bind=engine)
        if settings.auto_seed:
            with SessionLocal() as db:
                seed_initial_data(db)

    return app


app = create_app()
