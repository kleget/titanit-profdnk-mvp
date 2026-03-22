from __future__ import annotations

import importlib
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "invite_schedule.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "invite-schedule-secret")
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


def _dt_local(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%dT%H:%M")


def test_invite_link_start_deadline_and_personal_single_use(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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
                "title": "Ссылки с расписанием",
                "description": "Проверка start_at/expires_at/single_use",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Блок"],
                "q_text[]": ["Да/нет"],
                "q_key[]": ["yes_no_key"],
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
        from app.models import InviteLink, Test, TestSection

        with SessionLocal() as session:
            created_test = session.scalar(
                select(Test)
                .where(Test.id == test_id)
                .options(selectinload(Test.sections).selectinload(TestSection.questions))
            )
            assert created_test is not None
            question_id = created_test.sections[0].questions[0].id

        now = datetime.now(timezone.utc)
        future_start = _dt_local(now + timedelta(hours=2))
        past_start = _dt_local(now - timedelta(days=2))
        past_end = _dt_local(now - timedelta(days=1))

        pending_link_response = post_form_with_csrf(
            client,
            f"/tests/{test_id}/links",
            data={
                "label": "Pending link",
                "start_at": future_start,
                "expires_at": "",
                "single_use": "false",
                "target_client_name": "",
            },
            csrf_page_path=f"/tests/{test_id}",
            follow_redirects=False,
        )
        assert pending_link_response.status_code == 303

        expired_link_response = post_form_with_csrf(
            client,
            f"/tests/{test_id}/links",
            data={
                "label": "Expired link",
                "start_at": past_start,
                "expires_at": past_end,
                "single_use": "false",
                "target_client_name": "",
            },
            csrf_page_path=f"/tests/{test_id}",
            follow_redirects=False,
        )
        assert expired_link_response.status_code == 303

        personal_link_response = post_form_with_csrf(
            client,
            f"/tests/{test_id}/links",
            data={
                "label": "Personal link",
                "single_use": "true",
                "target_client_name": "Иван Иванов",
            },
            csrf_page_path=f"/tests/{test_id}",
            follow_redirects=False,
        )
        assert personal_link_response.status_code == 303

        with SessionLocal() as session:
            links = session.scalars(select(InviteLink).where(InviteLink.test_id == test_id)).all()
            links_map = {link.label: link for link in links}
            pending_token = links_map["Pending link"].token
            expired_token = links_map["Expired link"].token
            personal_token = links_map["Personal link"].token

        pending_page = client.get(f"/t/{pending_token}")
        assert pending_page.status_code == 404
        assert "ещё не активна" in pending_page.text

        expired_page = client.get(f"/t/{expired_token}")
        assert expired_page.status_code == 404
        assert "истёк" in expired_page.text

        wrong_person = post_form_with_csrf(
            client,
            f"/t/{personal_token}",
            data={
                "client_full_name": "Другой Клиент",
                f"q_{question_id}": "true",
            },
            csrf_page_path=f"/t/{personal_token}",
            follow_redirects=False,
        )
        assert wrong_person.status_code == 400
        assert "предназначена для другого клиента" in wrong_person.text

        correct_person = post_form_with_csrf(
            client,
            f"/t/{personal_token}",
            data={
                "client_full_name": "Иван Иванов",
                f"q_{question_id}": "true",
            },
            csrf_page_path=f"/t/{personal_token}",
            follow_redirects=False,
        )
        assert correct_person.status_code == 303

        second_try = client.get(f"/t/{personal_token}")
        assert second_try.status_code == 404
