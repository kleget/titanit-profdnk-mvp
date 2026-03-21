from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "admin_audit.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "admin-audit-secret")
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


def test_admin_actions_are_written_to_audit_log(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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

        create_response = post_form_with_csrf(
            client,
            "/admin/psychologists",
            data={
                "full_name": "Аудит Психолог",
                "email": "audit-psychologist@demo.local",
                "phone": "+79998887766",
                "password": "StrongPass1",
                "access_until": "2026-12-31",
            },
            csrf_page_path="/admin",
            follow_redirects=False,
        )
        assert create_response.status_code == 303

        from app.db import SessionLocal
        from app.models import AdminAuditLog, User

        with SessionLocal() as session:
            target_user = session.scalar(
                select(User).where(User.email == "audit-psychologist@demo.local")
            )
            assert target_user is not None
            target_user_id = target_user.id

        toggle_response = post_form_with_csrf(
            client,
            f"/admin/psychologists/{target_user_id}/toggle-block",
            data={},
            csrf_page_path="/admin",
            follow_redirects=False,
        )
        assert toggle_response.status_code == 303

        access_response = post_form_with_csrf(
            client,
            f"/admin/psychologists/{target_user_id}/access",
            data={"access_until": "2027-01-20"},
            csrf_page_path="/admin",
            follow_redirects=False,
        )
        assert access_response.status_code == 303

        with SessionLocal() as session:
            logs = session.scalars(
                select(AdminAuditLog)
                .where(AdminAuditLog.target_user_id == target_user_id)
                .order_by(AdminAuditLog.created_at.asc())
            ).all()
            actions = [item.action for item in logs]
            assert "psychologist_created" in actions
            assert "psychologist_blocked" in actions
            assert "psychologist_access_updated" in actions
