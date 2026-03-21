from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "formula_logic.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "formula-logic-secret")
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


def _base_manual_form_payload() -> dict[str, object]:
    return {
        "title": "Проверка формул",
        "description": "Валидация конфликтов логики",
        "allow_client_report": "true",
        "required_client_fields": ["full_name"],
        "section_titles[]": ["Блок"],
        "q_text[]": ["Оцените цифровые навыки"],
        "q_type[]": ["rating"],
        "q_required[]": ["true"],
        "q_options[]": [""],
        "q_min[]": ["1"],
        "q_max[]": ["5"],
        "q_weight[]": ["1"],
        "q_section[]": ["Блок"],
        "rt_client[]": ["profile", "summary_metrics", "answers"],
        "rt_psychologist[]": ["profile", "summary_metrics", "derived_metrics", "answers"],
    }


def test_manual_builder_rejects_unknown_formula_variable(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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

        payload = _base_manual_form_payload()
        payload.update(
            {
                "metric_key[]": ["bad_metric"],
                "metric_label[]": ["Плохая метрика"],
                "metric_expression[]": ["unknown_metric + score_percent"],
                "metric_description[]": [""],
            }
        )
        response = post_form_with_csrf(
            client,
            "/tests/new/manual",
            data=payload,
            csrf_page_path="/tests/new",
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "неизвестную переменную" in response.text


def test_manual_builder_rejects_forward_formula_reference(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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

        payload = _base_manual_form_payload()
        payload.update(
            {
                "metric_key[]": ["metric_a", "metric_b"],
                "metric_label[]": ["Метрика A", "Метрика B"],
                "metric_expression[]": ["metric_b + 1", "score_percent + 5"],
                "metric_description[]": ["", ""],
            }
        )
        response = post_form_with_csrf(
            client,
            "/tests/new/manual",
            data=payload,
            csrf_page_path="/tests/new",
            follow_redirects=False,
        )
        assert response.status_code == 400
        assert "объявлена ниже" in response.text
