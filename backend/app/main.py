from __future__ import annotations

from contextlib import asynccontextmanager
import logging
import secrets
from pathlib import Path
from time import perf_counter
from urllib.parse import urlsplit, urlunsplit

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import text
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from app.config import settings
from app.db import Base, engine, SessionLocal
from app.routers import admin, api, auth, psychologist, public
from app.services.seed import seed_initial_data
from app.web import templates


REDIRECT_STATUSES = {301, 302, 303, 307, 308}
ERROR_PAGE_CONTENT = {
    400: {
        "title": "Ошибка запроса",
        "message": "Проверьте заполнение полей и повторите попытку.",
        "action_href": "/",
        "action_label": "Вернуться на главную",
    },
    403: {
        "title": "Доступ ограничен",
        "message": "Для этого действия нужны другие права или активный доступ.",
        "action_href": "/login",
        "action_label": "Перейти ко входу",
    },
    404: {
        "title": "Страница не найдена",
        "message": "Запрошенный адрес не существует или был перемещён.",
        "action_href": "/",
        "action_label": "На главную",
    },
    500: {
        "title": "Внутренняя ошибка сервера",
        "message": "Мы уже зафиксировали проблему. Попробуйте обновить страницу чуть позже.",
        "action_href": "/",
        "action_label": "Обновить страницу",
    },
}

request_logger = logging.getLogger("profdnk.request")
startup_logger = logging.getLogger("profdnk.startup")
error_logger = logging.getLogger("profdnk.error")


def _configure_logging() -> None:
    log_level = getattr(logging, settings.log_level, logging.INFO)
    if logging.getLogger().handlers:
        logging.getLogger().setLevel(log_level)
        return
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )


def _sanitize_database_url(raw_url: str) -> str:
    parsed = urlsplit(raw_url)
    if not parsed.netloc or "@" not in parsed.netloc:
        return raw_url
    credentials, host = parsed.netloc.rsplit("@", 1)
    if ":" in credentials:
        username, _password = credentials.split(":", 1)
        safe_netloc = f"{username}:***@{host}"
    else:
        safe_netloc = parsed.netloc
    return urlunsplit(
        (parsed.scheme, safe_netloc, parsed.path, parsed.query, parsed.fragment)
    )


def _wants_html_response(request: Request) -> bool:
    path = request.url.path.lower()
    if path.startswith("/api") or path.endswith(".json"):
        return False
    accept = request.headers.get("accept", "").lower()
    if "application/json" in accept and "text/html" not in accept:
        return False
    return "text/html" in accept or "*/*" in accept or not accept


def _error_template_context(status_code: int, detail: str | None, request_id: str) -> dict[str, str]:
    base = ERROR_PAGE_CONTENT.get(status_code) or ERROR_PAGE_CONTENT[500]
    message = base["message"]
    if status_code in {400, 403} and detail:
        message = detail
    return {
        "title": f"Ошибка {status_code}",
        "status_code": str(status_code),
        "error_title": base["title"],
        "error_message": message,
        "request_id": request_id,
        "action_href": base["action_href"],
        "action_label": base["action_label"],
    }


def _run_startup_tasks() -> None:
    startup_logger.info(
        "startup env=%s base_url=%s database=%s auto_create_schema=%s auto_seed=%s",
        settings.app_env,
        settings.base_url,
        _sanitize_database_url(settings.database_url),
        settings.auto_create_schema,
        settings.auto_seed,
    )
    with engine.connect() as connection:
        connection.execute(text("SELECT 1"))
    startup_logger.info("database connectivity check passed")

    if settings.auto_create_schema:
        Base.metadata.create_all(bind=engine)
        startup_logger.info("database schema synchronization executed (AUTO_CREATE_SCHEMA=true)")
    else:
        startup_logger.info("database schema synchronization skipped (AUTO_CREATE_SCHEMA=false)")

    if settings.auto_seed:
        with SessionLocal() as db:
            seed_initial_data(db)
        startup_logger.info("seed data applied (AUTO_SEED=true)")
    else:
        startup_logger.info("seed data skipped (AUTO_SEED=false)")


@asynccontextmanager
async def lifespan(_app: FastAPI):  # type: ignore[no-untyped-def]
    _run_startup_tasks()
    yield


def create_app() -> FastAPI:
    _configure_logging()
    app = FastAPI(
        title="ПрофДНК API",
        description="Минимальная версия платформы ПрофДНК для хакатона ТИТАНИТ",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.add_middleware(
        SessionMiddleware,
        secret_key=settings.app_secret_key,
        session_cookie="profdnk_session",
        same_site=settings.session_same_site,
        https_only=settings.session_https_only,
        max_age=60 * 60 * 24 * 7,
    )

    @app.middleware("http")
    async def request_logging_middleware(request: Request, call_next):  # type: ignore[no-untyped-def]
        request_id = request.headers.get("X-Request-ID") or secrets.token_hex(8)
        request.state.request_id = request_id
        started_at = perf_counter()
        try:
            response = await call_next(request)
        except Exception:
            duration_ms = round((perf_counter() - started_at) * 1000, 2)
            error_logger.exception(
                "request_failed id=%s method=%s path=%s duration_ms=%.2f",
                request_id,
                request.method,
                request.url.path,
                duration_ms,
            )
            raise

        duration_ms = round((perf_counter() - started_at) * 1000, 2)
        log_method = request_logger.debug if request.url.path.startswith("/static/") else request_logger.info
        log_method(
            "request id=%s method=%s path=%s status=%s duration_ms=%.2f",
            request_id,
            request.method,
            request.url.path,
            response.status_code,
            duration_ms,
        )
        response.headers["X-Request-ID"] = request_id
        return response

    static_dir = Path(__file__).resolve().parent / "static"
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

    app.include_router(auth.router)
    app.include_router(admin.router)
    app.include_router(psychologist.router)
    app.include_router(public.router)
    app.include_router(api.router)

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(request: Request, exc: StarletteHTTPException):  # type: ignore[no-untyped-def]
        location = (exc.headers or {}).get("Location")
        if location and exc.status_code in REDIRECT_STATUSES:
            return RedirectResponse(
                url=location,
                status_code=exc.status_code,
                headers=exc.headers,
            )

        request_id = getattr(request.state, "request_id", "unknown")
        detail = exc.detail if isinstance(exc.detail, str) else None

        if _wants_html_response(request):
            context = _error_template_context(exc.status_code, detail, request_id)
            return templates.TemplateResponse(
                request,
                "error.html",
                context,
                status_code=exc.status_code,
                headers=exc.headers,
            )

        payload = {"detail": exc.detail, "request_id": request_id}
        return JSONResponse(payload, status_code=exc.status_code, headers=exc.headers)

    @app.exception_handler(RequestValidationError)
    async def request_validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, "request_id", "unknown")
        first_error = exc.errors()[0] if exc.errors() else {}
        detail = str(first_error.get("msg") or "Некорректные данные запроса")
        if _wants_html_response(request):
            context = _error_template_context(400, detail, request_id)
            return templates.TemplateResponse(
                request,
                "error.html",
                context,
                status_code=400,
            )
        return JSONResponse(
            {
                "detail": "Validation error",
                "errors": exc.errors(),
                "request_id": request_id,
            },
            status_code=422,
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):  # type: ignore[no-untyped-def]
        request_id = getattr(request.state, "request_id", "unknown")
        error_logger.exception(
            "unhandled_error id=%s method=%s path=%s",
            request_id,
            request.method,
            request.url.path,
        )
        if _wants_html_response(request):
            context = _error_template_context(500, None, request_id)
            return templates.TemplateResponse(
                request,
                "error.html",
                context,
                status_code=500,
            )
        return JSONResponse(
            {"detail": "Internal server error", "request_id": request_id},
            status_code=500,
        )

    return app


app = create_app()
