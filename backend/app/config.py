from __future__ import annotations

import os
from dataclasses import dataclass


def _to_bool(value: str | None, default: bool = False) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_secret_key: str
    database_url: str
    base_url: str
    auto_seed: bool


settings = Settings(
    app_secret_key=os.getenv("APP_SECRET_KEY", "change-me"),
    database_url=os.getenv(
        "DATABASE_URL", "postgresql+psycopg2://profdnk:profdnk@localhost:5432/profdnk"
    ),
    base_url=os.getenv("BASE_URL", "http://localhost:8000").rstrip("/"),
    auto_seed=_to_bool(os.getenv("AUTO_SEED"), default=True),
)

