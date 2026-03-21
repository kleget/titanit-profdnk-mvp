from __future__ import annotations

import importlib
import re
import sys
from pathlib import Path

from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import selectinload


def _reload_app_with_temp_db(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    db_path = tmp_path / "clone_test.sqlite3"
    monkeypatch.setenv("APP_SECRET_KEY", "clone-test-secret")
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


def test_clone_test_creates_full_copy_without_invite_links(tmp_path: Path, monkeypatch):  # type: ignore[no-untyped-def]
    main_module = _reload_app_with_temp_db(tmp_path, monkeypatch)
    app = main_module.create_app()

    with TestClient(app) as client:
        login_response = client.post(
            "/login",
            data={"email": "psychologist@demo.local", "password": "demo12345"},
            follow_redirects=False,
        )
        assert login_response.status_code == 303

        create_response = client.post(
            "/tests/new/manual",
            data={
                "title": "Исходный тест для клонирования",
                "description": "Проверка полного дублирования структуры.",
                "allow_client_report": "true",
                "required_client_fields": ["full_name", "email", "age"],
                "cf_key[]": ["city"],
                "cf_label[]": ["Город"],
                "cf_type[]": ["text"],
                "cf_required[]": ["true"],
                "cf_placeholder[]": ["Например: Ростов-на-Дону"],
                "section_titles[]": ["Профиль"],
                "q_text[]": ["Готовы ли вы к смене траектории?"],
                "q_type[]": ["yes_no"],
                "q_required[]": ["true"],
                "q_options[]": [""],
                "q_min[]": [""],
                "q_max[]": [""],
                "q_weight[]": ["1.2"],
                "q_section[]": ["Профиль"],
                "metric_key[]": ["readiness_index"],
                "metric_label[]": ["Индекс готовности"],
                "metric_expression[]": ["round((score_percent + completion_percent) / 2, 2)"],
                "metric_description[]": ["Сводная оценка готовности по тесту."],
                "rt_client[]": ["profile", "summary_metrics", "answers"],
                "rt_psychologist[]": [
                    "profile",
                    "summary_metrics",
                    "charts",
                    "derived_metrics",
                    "answers",
                ],
            },
            follow_redirects=False,
        )
        assert create_response.status_code == 303
        source_match = re.search(r"/tests/(\d+)", create_response.headers["location"])
        assert source_match is not None
        source_test_id = int(source_match.group(1))

        create_link_response = client.post(
            f"/tests/{source_test_id}/links",
            data={"label": "Campaign-Source", "usage_limit": ""},
            follow_redirects=False,
        )
        assert create_link_response.status_code == 303

        clone_response = client.post(f"/tests/{source_test_id}/clone", follow_redirects=False)
        assert clone_response.status_code == 303
        clone_match = re.search(r"/tests/(\d+)", clone_response.headers["location"])
        assert clone_match is not None
        cloned_test_id = int(clone_match.group(1))
        assert cloned_test_id != source_test_id

        from app.db import SessionLocal
        from app.models import Test, TestSection
        from app.services.client_fields import normalize_client_fields_config

        with SessionLocal() as session:
            source_test = session.scalar(
                select(Test)
                .where(Test.id == source_test_id)
                .options(
                    selectinload(Test.sections).selectinload(TestSection.questions),
                    selectinload(Test.formulas),
                    selectinload(Test.invite_links),
                )
            )
            cloned_test = session.scalar(
                select(Test)
                .where(Test.id == cloned_test_id)
                .options(
                    selectinload(Test.sections).selectinload(TestSection.questions),
                    selectinload(Test.formulas),
                    selectinload(Test.invite_links),
                )
            )
            assert source_test is not None
            assert cloned_test is not None

            assert cloned_test.psychologist_id == source_test.psychologist_id
            assert cloned_test.title.startswith(source_test.title)
            assert "(копия)" in cloned_test.title
            assert cloned_test.share_token != source_test.share_token
            assert cloned_test.allow_client_report == source_test.allow_client_report

            source_fields = normalize_client_fields_config(source_test.required_client_fields)
            cloned_fields = normalize_client_fields_config(cloned_test.required_client_fields)
            assert source_fields == cloned_fields

            assert len(cloned_test.sections) == len(source_test.sections)
            assert sum(len(section.questions) for section in cloned_test.sections) == sum(
                len(section.questions) for section in source_test.sections
            )
            assert len(cloned_test.formulas) == len(source_test.formulas)

            assert len(source_test.invite_links) == 1
            assert len(cloned_test.invite_links) == 0
