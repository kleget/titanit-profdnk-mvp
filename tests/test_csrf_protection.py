from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "csrf.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "csrf-secret")
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


def test_login_requires_csrf_token(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch)
    app = main_module.create_app()

    with TestClient(app) as client:
        response = client.post(
            "/login",
            data={"email": "admin@profdnk.local", "password": "admin123"},
            follow_redirects=False,
        )
        assert response.status_code == 403
        assert "CSRF" in response.text


def test_protected_form_rejects_missing_csrf_after_login(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch)
    app = main_module.create_app()

    with TestClient(app) as client:
        login_response = post_form_with_csrf(
            client,
            "/login",
            data={"email": "psychologist@demo.local", "password": "demo12345"},
            csrf_page_path="/login",
            follow_redirects=False,
        )
        assert login_response.status_code == 303

        create_without_csrf = client.post(
            "/tests/new/manual",
            data={
                "title": "Без CSRF",
                "description": "Проверка блокировки",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Секция"],
                "q_text[]": ["Вопрос?"],
                "q_type[]": ["yes_no"],
                "q_required[]": ["true"],
                "q_options[]": [""],
                "q_min[]": [""],
                "q_max[]": [""],
                "q_weight[]": ["1"],
                "q_section[]": ["Секция"],
                "rt_client[]": ["profile", "summary_metrics", "answers"],
                "rt_psychologist[]": ["profile", "summary_metrics", "answers"],
            },
            follow_redirects=False,
        )
        assert create_without_csrf.status_code == 403
        assert "CSRF" in create_without_csrf.text
