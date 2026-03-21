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
    db_path = tmp_path / "integration.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "integration-secret-key")
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


def test_end_to_end_manual_builder_submission_and_reports(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch)
    app = main_module.create_app()

    with TestClient(app) as client:
        login_response = post_form_with_csrf(
            client,
            "/login",
            data={
                "email": "psychologist@demo.local",
                "password": "demo12345",
            },
            csrf_page_path="/login",
            follow_redirects=False,
        )
        assert login_response.status_code == 303
        assert login_response.headers["location"] == "/dashboard"

        create_response = post_form_with_csrf(
            client,
            "/tests/new/manual",
            data={
                "title": "Интеграционный тест методики",
                "description": "Проверка полного потока",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Базовый раздел"],
                "q_text[]": ["Готовы ли работать удалённо?"],
                "q_type[]": ["yes_no"],
                "q_required[]": ["true"],
                "q_options[]": [""],
                "q_min[]": [""],
                "q_max[]": [""],
                "q_weight[]": ["1"],
                "q_section[]": ["Базовый раздел"],
                "rt_client[]": ["profile", "summary_metrics", "answers"],
                "rt_psychologist[]": [
                    "profile",
                    "summary_metrics",
                    "charts",
                    "derived_metrics",
                    "answers",
                ],
            },
            csrf_page_path="/tests/new",
            follow_redirects=False,
        )
        assert create_response.status_code == 303
        location = create_response.headers["location"]
        assert location.startswith("/tests/")
        test_id_match = re.search(r"/tests/(\d+)", location)
        assert test_id_match is not None
        test_id = int(test_id_match.group(1))

        from app.db import SessionLocal
        from app.models import Submission, Test, TestSection

        with SessionLocal() as session:
            created_test = session.scalar(
                select(Test)
                .where(Test.id == test_id)
                .options(selectinload(Test.sections).selectinload(TestSection.questions))
            )
            assert created_test is not None
            assert created_test.share_token
            question = created_test.sections[0].questions[0]
            token = created_test.share_token

        submit_response = post_form_with_csrf(
            client,
            f"/t/{token}",
            data={
                "client_full_name": "Клиент Интеграции",
                f"q_{question.id}": "true",
            },
            csrf_page_path=f"/t/{token}",
            follow_redirects=False,
        )
        assert submit_response.status_code == 303
        done_location = submit_response.headers["location"]
        assert done_location.startswith(f"/t/{token}/done/")

        done_page = client.get(done_location)
        assert done_page.status_code == 200
        assert "Тест завершён" in done_page.text

        submissions_response = client.get(f"/tests/{test_id}/submissions.json")
        assert submissions_response.status_code == 200
        submissions_payload = submissions_response.json()
        assert len(submissions_payload) == 1
        submission_id = int(submissions_payload[0]["id"])

        html_report = client.get(f"/reports/{submission_id}/psychologist.html")
        assert html_report.status_code == 200
        assert "Отчёт для профориентолога" in html_report.text

        docx_report = client.get(f"/reports/{submission_id}/psychologist.docx")
        assert docx_report.status_code == 200
        assert docx_report.content.startswith(b"PK")

        with SessionLocal() as session:
            stored_submissions = session.scalars(
                select(Submission).where(Submission.test_id == test_id)
            ).all()
            assert len(stored_submissions) == 1
