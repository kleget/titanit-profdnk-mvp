from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "admin_password_policy.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "admin-password-policy-secret")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BASE_URL", "http://testserver")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTO_SEED", "true")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("SESSION_HTTPS_ONLY", "false")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    return importlib.import_module("app.main")


def test_admin_create_psychologist_password_policy(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch)
    app = main_module.create_app()

    with TestClient(app) as client:
        login_response = post_form_with_csrf(
            client,
            "/login",
            data={"email": "admin@profdnk.local", "password": "admin123"},
            csrf_page_path="/login",
            follow_redirects=False,
        )
        assert login_response.status_code == 303
        assert login_response.headers["location"] == "/admin"

        weak_password_response = post_form_with_csrf(
            client,
            "/admin/psychologists",
            data={
                "full_name": "Слабый Пароль",
                "email": "weak-password@demo.local",
                "phone": "+79990001122",
                "password": "weakpass",
                "access_until": "",
            },
            csrf_page_path="/admin",
            follow_redirects=False,
        )
        assert weak_password_response.status_code == 400
        assert "Пароль должен содержать хотя бы одну заглавную букву." in weak_password_response.text

        strong_password_response = post_form_with_csrf(
            client,
            "/admin/psychologists",
            data={
                "full_name": "Сильный Пароль",
                "email": "strong-password@demo.local",
                "phone": "+79990001123",
                "password": "StrongPass1",
                "access_until": "",
            },
            csrf_page_path="/admin",
            follow_redirects=False,
        )
        assert strong_password_response.status_code == 303
        assert (
            strong_password_response.headers["location"]
            == "/admin?notice=psychologist_created&notice_type=success"
        )

        from app.db import SessionLocal
        from app.models import User

        with SessionLocal() as session:
            weak_user = session.scalar(select(User).where(User.email == "weak-password@demo.local"))
            strong_user = session.scalar(select(User).where(User.email == "strong-password@demo.local"))
            assert weak_user is None
            assert strong_user is not None
