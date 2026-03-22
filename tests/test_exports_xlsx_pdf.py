from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "exports.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "exports-secret")
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


def test_xlsx_pdf_exports_and_quick_share_button_available(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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

        create_response = post_form_with_csrf(
            client,
            "/tests/new/manual",
            data={
                "title": "Экспорты и шаринг",
                "description": "Проверка XLSX/PDF и кнопки шаринга",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Блок"],
                "q_text[]": ["Готовы ли вы?"],
                "q_key[]": ["ready_key"],
                "q_type[]": ["yes_no"],
                "q_required[]": ["true"],
                "q_options[]": [""],
                "q_min[]": [""],
                "q_max[]": [""],
                "q_weight[]": ["1"],
                "q_section[]": ["Блок"],
                "rt_client[]": ["profile", "summary_metrics", "answers"],
                "rt_psychologist[]": ["profile", "summary_metrics", "answers"],
            },
            csrf_page_path="/tests/new",
            follow_redirects=False,
        )
        assert create_response.status_code == 303
        match = re.search(r"/tests/(\d+)", create_response.headers["location"])
        assert match is not None
        test_id = int(match.group(1))

        from app.db import SessionLocal
        from app.models import Test, TestSection

        with SessionLocal() as session:
            created_test = session.scalar(
                select(Test)
                .where(Test.id == test_id)
                .options(selectinload(Test.sections).selectinload(TestSection.questions))
            )
            assert created_test is not None
            token = created_test.share_token
            question_id = created_test.sections[0].questions[0].id

        submit_response = post_form_with_csrf(
            client,
            f"/t/{token}",
            data={
                "client_full_name": "Клиент экспорта",
                f"q_{question_id}": "true",
            },
            csrf_page_path=f"/t/{token}",
            follow_redirects=False,
        )
        assert submit_response.status_code == 303

        detail_page = client.get(f"/tests/{test_id}")
        assert detail_page.status_code == 200
        assert "Экспорт XLSX" in detail_page.text
        assert "PDF по кампаниям" in detail_page.text
        assert "Поделиться клиенту" in detail_page.text

        xlsx_response = client.get(f"/tests/{test_id}/submissions.xlsx")
        assert xlsx_response.status_code == 200
        assert (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            in xlsx_response.headers.get("content-type", "")
        )
        assert xlsx_response.content.startswith(b"PK")

        pdf_response = client.get(f"/tests/{test_id}/campaign-report.pdf")
        assert pdf_response.status_code == 200
        assert "application/pdf" in pdf_response.headers.get("content-type", "")
        assert pdf_response.content.startswith(b"%PDF")
