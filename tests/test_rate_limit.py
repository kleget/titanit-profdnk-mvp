from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(
    tmp_path: Path,
    monkeypatch,  # type: ignore[no-untyped-def]
    *,
    login_limit: int = 2,
    login_window_seconds: int = 60,
    submit_limit: int = 1,
    submit_window_seconds: int = 60,
):
    db_path = tmp_path / "rate_limit.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "rate-limit-secret-key")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path.as_posix()}")
    monkeypatch.setenv("BASE_URL", "http://testserver")
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv("AUTO_SEED", "true")
    monkeypatch.setenv("AUTO_CREATE_SCHEMA", "true")
    monkeypatch.setenv("SESSION_HTTPS_ONLY", "false")
    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    monkeypatch.setenv("LOGIN_RATE_LIMIT_ATTEMPTS", str(login_limit))
    monkeypatch.setenv("LOGIN_RATE_LIMIT_WINDOW_SECONDS", str(login_window_seconds))
    monkeypatch.setenv("SUBMIT_RATE_LIMIT_ATTEMPTS", str(submit_limit))
    monkeypatch.setenv("SUBMIT_RATE_LIMIT_WINDOW_SECONDS", str(submit_window_seconds))

    for module_name in list(sys.modules):
        if module_name == "app" or module_name.startswith("app."):
            del sys.modules[module_name]

    return importlib.import_module("app.main")


def test_login_rate_limit_blocks_after_threshold(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch, login_limit=2)
    app = main_module.create_app()

    with TestClient(app) as client:
        payload = {
            "email": "psychologist@demo.local",
            "password": "wrong-password",
        }
        first_attempt = post_form_with_csrf(
            client,
            "/login",
            data=payload,
            csrf_page_path="/login",
            follow_redirects=False,
        )
        second_attempt = post_form_with_csrf(
            client,
            "/login",
            data=payload,
            csrf_page_path="/login",
            follow_redirects=False,
        )
        assert first_attempt.status_code == 400
        assert second_attempt.status_code == 400

        blocked_attempt = post_form_with_csrf(
            client,
            "/login",
            data=payload,
            csrf_page_path="/login",
            follow_redirects=False,
        )
        assert blocked_attempt.status_code == 429
        assert "Слишком много попыток входа" in blocked_attempt.text
        assert blocked_attempt.headers.get("x-ratelimit-limit") == "2"
        retry_after = blocked_attempt.headers.get("retry-after")
        assert retry_after is not None
        assert int(retry_after) > 0


def test_submit_rate_limit_blocks_after_threshold(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch, submit_limit=1)
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

        create_response = post_form_with_csrf(
            client,
            "/tests/new/manual",
            data={
                "title": "Тест с лимитом отправки",
                "description": "Проверка защиты submit",
                "allow_client_report": "false",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Блок"],
                "q_text[]": ["Да/нет вопрос"],
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
        location = create_response.headers["location"]
        match = re.search(r"/tests/(\d+)", location)
        assert match is not None
        test_id = int(match.group(1))

        from app.db import SessionLocal
        from app.models import Submission, Test, TestSection

        with SessionLocal() as session:
            created_test = session.scalar(
                select(Test)
                .where(Test.id == test_id)
                .options(selectinload(Test.sections).selectinload(TestSection.questions))
            )
            assert created_test is not None
            token = created_test.share_token
            question = created_test.sections[0].questions[0]

        first_submit = post_form_with_csrf(
            client,
            f"/t/{token}",
            data={"client_full_name": "Клиент 1", f"q_{question.id}": "true"},
            csrf_page_path=f"/t/{token}",
            follow_redirects=False,
        )
        assert first_submit.status_code == 303

        blocked_submit = post_form_with_csrf(
            client,
            f"/t/{token}",
            data={"client_full_name": "Клиент 2", f"q_{question.id}": "true"},
            csrf_page_path=f"/t/{token}",
            follow_redirects=False,
        )
        assert blocked_submit.status_code == 429
        assert "Слишком много отправок анкеты" in blocked_submit.text
        assert blocked_submit.headers.get("x-ratelimit-limit") == "1"
        retry_after = blocked_submit.headers.get("retry-after")
        assert retry_after is not None
        assert int(retry_after) > 0

        with SessionLocal() as session:
            submissions_count = session.scalar(
                select(func.count(Submission.id)).where(Submission.test_id == test_id)
            )
            assert submissions_count == 1
