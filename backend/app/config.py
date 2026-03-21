from __future__ import annotations

import os
import secrets
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _normalize_env(value: str | None) -> str:
    return (value or "development").strip().lower()


def _to_same_site(value: str | None, default: str = "lax") -> str:
    normalized = (value or default).strip().lower()
    if normalized not in {"lax", "strict", "none"}:
        return default
    return normalized


def _normalize_log_level(value: str | None, default: str = "INFO") -> str:
    normalized = (value or default).strip().upper()
    if normalized not in {"CRITICAL", "ERROR", "WARNING", "INFO", "DEBUG"}:
        return default
    return normalized


def _to_int(value: str | None, default: int, *, min_value: int, max_value: int) -> int:
    if value is None:
        return default
    try:
        parsed = int(value.strip())
    except (TypeError, ValueError):
        return default
    if parsed < min_value or parsed > max_value:
        return default
    return parsed


@dataclass(frozen=True)
class Settings:
    app_secret_key: str
    database_url: str
    base_url: str
    app_env: str
    auto_seed: bool
    auto_create_schema: bool
    session_https_only: bool
    session_same_site: str
    log_level: str
    smtp_host: str
    smtp_port: int
    smtp_user: str
    smtp_password: str
    smtp_from: str
    smtp_tls: bool
    smtp_timeout_seconds: int
    smtp_enabled: bool
    login_rate_limit_attempts: int
    login_rate_limit_window_seconds: int
    submit_rate_limit_attempts: int
    submit_rate_limit_window_seconds: int


_app_env = _normalize_env(os.getenv("APP_ENV"))
_is_production = _app_env in {"prod", "production"}

_app_secret_key = os.getenv("APP_SECRET_KEY", "").strip()
if not _app_secret_key:
    if _is_production:
        raise RuntimeError("APP_SECRET_KEY is required in production environment")
    # Для локальной разработки используем случайный ключ, чтобы не хранить небезопасный дефолт.
    _app_secret_key = secrets.token_urlsafe(32)

_database_url = os.getenv("DATABASE_URL", "").strip()
if not _database_url:
    if _is_production:
        raise RuntimeError("DATABASE_URL is required in production environment")
    _database_url = "sqlite:///./dev.db"

_base_url = os.getenv("BASE_URL", "http://localhost:8000").rstrip("/")

_smtp_user = os.getenv("SMTP_USER", "").strip()
_smtp_password = os.getenv("SMTP_PASSWORD", "").strip()
_smtp_from = os.getenv("SMTP_FROM", "").strip() or _smtp_user
_smtp_enabled_default = bool(_smtp_user and _smtp_password and _smtp_from)

settings = Settings(
    app_secret_key=_app_secret_key,
    database_url=_database_url,
    base_url=_base_url,
    app_env=_app_env,
    auto_seed=_to_bool(os.getenv("AUTO_SEED"), default=False),
    auto_create_schema=_to_bool(
        os.getenv("AUTO_CREATE_SCHEMA"),
        default=not _is_production,
    ),
    session_https_only=_to_bool(
        os.getenv("SESSION_HTTPS_ONLY"),
        default=_base_url.startswith("https://"),
    ),
    session_same_site=_to_same_site(os.getenv("SESSION_SAME_SITE"), default="lax"),
    log_level=_normalize_log_level(os.getenv("LOG_LEVEL"), default="INFO"),
    smtp_host=os.getenv("SMTP_HOST", "smtp.gmail.com").strip() or "smtp.gmail.com",
    smtp_port=_to_int(os.getenv("SMTP_PORT"), default=587, min_value=1, max_value=65535),
    smtp_user=_smtp_user,
    smtp_password=_smtp_password,
    smtp_from=_smtp_from,
    smtp_tls=_to_bool(os.getenv("SMTP_TLS"), default=True),
    smtp_timeout_seconds=_to_int(
        os.getenv("SMTP_TIMEOUT_SECONDS"),
        default=15,
        min_value=3,
        max_value=120,
    ),
    smtp_enabled=_to_bool(os.getenv("SMTP_ENABLED"), default=_smtp_enabled_default),
    login_rate_limit_attempts=_to_int(
        os.getenv("LOGIN_RATE_LIMIT_ATTEMPTS"),
        default=8,
        min_value=1,
        max_value=1000,
    ),
    login_rate_limit_window_seconds=_to_int(
        os.getenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS"),
        default=300,
        min_value=10,
        max_value=86400,
    ),
    submit_rate_limit_attempts=_to_int(
        os.getenv("SUBMIT_RATE_LIMIT_ATTEMPTS"),
        default=30,
        min_value=1,
        max_value=5000,
    ),
    submit_rate_limit_window_seconds=_to_int(
        os.getenv("SUBMIT_RATE_LIMIT_WINDOW_SECONDS"),
        default=60,
        min_value=10,
        max_value=86400,
    ),
)
