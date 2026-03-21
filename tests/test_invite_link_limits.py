from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import func, select
from sqlalchemy.orm import selectinload

from tests.helpers import post_form_with_csrf


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "invite_limit.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "invite-limit-secret")
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


def test_named_invite_link_limit_deactivates_after_reaching_limit(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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
                "title": "Тест с лимитом ссылки",
                "description": "Проверка исчерпания ссылки",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Блок"],
                "q_text[]": ["Да/нет"],
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
        from app.models import InviteLink, Submission, Test, TestSection

        with SessionLocal() as session:
            created_test = session.scalar(
                select(Test)
                .where(Test.id == test_id)
                .options(selectinload(Test.sections).selectinload(TestSection.questions))
            )
            assert created_test is not None
            question = created_test.sections[0].questions[0]

        create_link_response = post_form_with_csrf(
            client,
            f"/tests/{test_id}/links",
            data={"label": "Campaign-1", "usage_limit": "1"},
            csrf_page_path=f"/tests/{test_id}",
            follow_redirects=False,
        )
        assert create_link_response.status_code == 303

        with SessionLocal() as session:
            invite_link = session.scalar(
                select(InviteLink)
                .where(InviteLink.test_id == test_id, InviteLink.label == "Campaign-1")
            )
            assert invite_link is not None
            assert invite_link.usage_limit == 1
            assert invite_link.usage_count == 0
            assert invite_link.is_active is True
            invite_token = invite_link.token
            share_token = session.scalar(select(Test.share_token).where(Test.id == test_id))

        first_submit = post_form_with_csrf(
            client,
            f"/t/{invite_token}",
            data={
                "client_full_name": "Клиент 1",
                f"q_{question.id}": "true",
            },
            csrf_page_path=f"/t/{invite_token}",
            follow_redirects=False,
        )
        assert first_submit.status_code == 303
        assert first_submit.headers["location"].startswith(f"/t/{share_token}/done/")

        with SessionLocal() as session:
            invite_link = session.scalar(select(InviteLink).where(InviteLink.token == invite_token))
            assert invite_link is not None
            assert invite_link.usage_count == 1
            assert invite_link.is_active is False
            submissions_count = session.scalar(
                select(func.count(Submission.id)).where(Submission.test_id == test_id)
            )
            assert submissions_count == 1

        closed_page = client.get(f"/t/{invite_token}")
        assert closed_page.status_code == 404

        second_submit = post_form_with_csrf(
            client,
            f"/t/{invite_token}",
            data={
                "client_full_name": "Клиент 2",
                f"q_{question.id}": "true",
            },
            csrf_page_path=f"/tests/{test_id}",
            follow_redirects=False,
        )
        assert second_submit.status_code == 404

        with SessionLocal() as session:
            submissions = session.scalars(select(Submission).where(Submission.test_id == test_id)).all()
            assert len(submissions) == 1
