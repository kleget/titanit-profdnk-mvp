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
    db_path = tmp_path / "campaign_csv.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "campaign-csv-secret")
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


def test_campaign_comparison_block_and_csv_export_work(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
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
                "title": "Campaign comparison",
                "description": "CSV export and grouped comparison",
                "allow_client_report": "true",
                "required_client_fields": ["full_name"],
                "section_titles[]": ["Block"],
                "q_text[]": ["Do you agree?"],
                "q_type[]": ["yes_no"],
                "q_required[]": ["true"],
                "q_options[]": [""],
                "q_min[]": [""],
                "q_max[]": [""],
                "q_weight[]": ["1"],
                "q_section[]": ["Block"],
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
            question = created_test.sections[0].questions[0]
            share_token = created_test.share_token

        for label in ("Campaign-A", "Campaign-B"):
            create_link_response = post_form_with_csrf(
                client,
                f"/tests/{test_id}/links",
                data={"label": label, "usage_limit": ""},
                csrf_page_path=f"/tests/{test_id}",
                follow_redirects=False,
            )
            assert create_link_response.status_code == 303

        with SessionLocal() as session:
            links = session.scalars(
                select(InviteLink).where(InviteLink.test_id == test_id)
            ).all()
            links_by_label = {item.label: item for item in links}
            token_a = links_by_label["Campaign-A"].token
            token_b = links_by_label["Campaign-B"].token

        submit_a = post_form_with_csrf(
            client,
            f"/t/{token_a}",
            data={
                "client_full_name": "Alice",
                f"q_{question.id}": "true",
            },
            csrf_page_path=f"/t/{token_a}",
            follow_redirects=False,
        )
        assert submit_a.status_code == 303

        submit_b = post_form_with_csrf(
            client,
            f"/t/{token_b}",
            data={
                "client_full_name": "Bob",
                f"q_{question.id}": "false",
            },
            csrf_page_path=f"/t/{token_b}",
            follow_redirects=False,
        )
        assert submit_b.status_code == 303

        submit_base = post_form_with_csrf(
            client,
            f"/t/{share_token}",
            data={
                "client_full_name": "Charlie",
                f"q_{question.id}": "true",
            },
            csrf_page_path=f"/t/{share_token}",
            follow_redirects=False,
        )
        assert submit_base.status_code == 303

        detail_page = client.get(f"/tests/{test_id}")
        assert detail_page.status_code == 200
        assert "Сравнение кампаний" in detail_page.text
        assert "Campaign-A" in detail_page.text
        assert "Campaign-B" in detail_page.text

        csv_response = client.get(f"/tests/{test_id}/submissions.csv")
        assert csv_response.status_code == 200
        assert "text/csv" in csv_response.headers.get("content-type", "")
        csv_text = csv_response.content.decode("utf-8-sig")
        assert "submission_id" in csv_text
        assert "source_label" in csv_text
        assert "score_percent" in csv_text
        assert "Campaign-A" in csv_text
        assert "Campaign-B" in csv_text
