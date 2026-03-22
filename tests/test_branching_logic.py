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
    db_path = tmp_path / "branching.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "branching-secret")
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


def test_branching_hides_required_question_until_condition_is_met(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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
                "title": "Тест с ветвлениями",
                "description": "Проверка ветвлений по секциям и вопросам",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Профиль", "Удалёнка"],
                "section_if_key[]": ["", "remote_ready"],
                "section_if_operator[]": ["", "equals"],
                "section_if_value[]": ["", "true"],
                "q_text[]": [
                    "Готовы работать удалённо?",
                    "Почему выбрали удалённый формат?",
                ],
                "q_key[]": ["remote_ready", "remote_reason"],
                "q_type[]": ["yes_no", "text"],
                "q_required[]": ["true", "true"],
                "q_options[]": ["", ""],
                "q_min[]": ["", ""],
                "q_max[]": ["", ""],
                "q_weight[]": ["1", "1"],
                "q_section[]": ["Профиль", "Удалёнка"],
                "q_if_key[]": ["", "remote_ready"],
                "q_if_operator[]": ["", "equals"],
                "q_if_value[]": ["", "true"],
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
            share_token = created_test.share_token
            questions_by_key = {
                question.key: question
                for section in created_test.sections
                for question in section.questions
            }

        # Ветка скрыта: обязательный вопрос из второй секции не должен блокировать отправку.
        submit_hidden = post_form_with_csrf(
            client,
            f"/t/{share_token}",
            data={
                "client_full_name": "Клиент 1",
                f"q_{questions_by_key['remote_ready'].id}": "false",
            },
            csrf_page_path=f"/t/{share_token}",
            follow_redirects=False,
        )
        assert submit_hidden.status_code == 303

        # Ветка открыта: без ответа на обязательный вопрос отправка должна блокироваться.
        submit_missing = post_form_with_csrf(
            client,
            f"/t/{share_token}",
            data={
                "client_full_name": "Клиент 2",
                f"q_{questions_by_key['remote_ready'].id}": "true",
            },
            csrf_page_path=f"/t/{share_token}",
            follow_redirects=False,
        )
        assert submit_missing.status_code == 400
        assert "Заполните обязательный вопрос" in submit_missing.text

        # Ветка открыта + заполнен обязательный вопрос: отправка успешна.
        submit_ok = post_form_with_csrf(
            client,
            f"/t/{share_token}",
            data={
                "client_full_name": "Клиент 3",
                f"q_{questions_by_key['remote_ready'].id}": "true",
                f"q_{questions_by_key['remote_reason'].id}": "Готов работать из дома",
            },
            csrf_page_path=f"/t/{share_token}",
            follow_redirects=False,
        )
        assert submit_ok.status_code == 303
