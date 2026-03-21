from __future__ import annotations

import importlib
import sys
from pathlib import Path

from fastapi.testclient import TestClient

from tests.helpers import fetch_csrf_token, post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "formula_preview.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "formula-preview-secret")
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


def test_formula_preview_evaluates_chain(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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

        csrf_token = fetch_csrf_token(client, "/tests/new")
        response = client.post(
            "/api/formulas/preview",
            json={
                "context": {
                    "score_percent": 70,
                    "completion_percent": 90,
                },
                "formulas": [
                    {
                        "key": "readiness_index",
                        "label": "Индекс готовности",
                        "expression": "round((score_percent + completion_percent) / 2, 2)",
                    },
                    {
                        "key": "dropout_risk",
                        "label": "Риск незавершения",
                        "expression": "round(max(0, 100 - readiness_index), 2)",
                    },
                ],
            },
            headers={"x-csrf-token": csrf_token},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["results"][0]["status"] == "ok"
        assert payload["results"][0]["value"] == 80.0
        assert payload["results"][1]["status"] == "ok"
        assert payload["results"][1]["value"] == 20.0
        assert payload["context"]["readiness_index"] == 80.0
        assert payload["context"]["dropout_risk"] == 20.0


def test_formula_preview_returns_error_for_unknown_variable(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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

        csrf_token = fetch_csrf_token(client, "/tests/new")
        response = client.post(
            "/api/formulas/preview",
            json={
                "context": {"score_percent": 65},
                "formulas": [
                    {
                        "key": "bad_formula",
                        "label": "Ошибка",
                        "expression": "unknown_metric + score_percent",
                    }
                ],
            },
            headers={"x-csrf-token": csrf_token},
        )
        assert response.status_code == 200
        payload = response.json()
        assert payload["results"][0]["status"] == "error"
        assert "Unknown variable" in payload["results"][0]["error"]
