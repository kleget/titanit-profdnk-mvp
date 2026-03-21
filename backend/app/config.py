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


@dataclass(frozen=True)
class Settings:
    app_secret_key: str
    database_url: str
    base_url: str
    app_env: str
    auto_seed: bool
    session_https_only: bool
    session_same_site: str


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

settings = Settings(
    app_secret_key=_app_secret_key,
    database_url=_database_url,
    base_url=_base_url,
    app_env=_app_env,
    auto_seed=_to_bool(os.getenv("AUTO_SEED"), default=False),
    session_https_only=_to_bool(
        os.getenv("SESSION_HTTPS_ONLY"),
        default=_base_url.startswith("https://"),
    ),
    session_same_site=_to_same_site(os.getenv("SESSION_SAME_SITE"), default="lax"),
)

