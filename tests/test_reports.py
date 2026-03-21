from __future__ import annotations

from datetime import datetime, timezone

from app.models import (
    Answer,
    Question,
    QuestionType,
    Submission,
    Test as SurveyTest,
    TestSection as SurveySection,
    User,
    UserRole,
)
from app.services.reports import build_docx_report, build_report_context, render_html_report


def _build_report_test_case() -> tuple[SurveyTest, Submission]:
    psychologist = User(
        id=10,
        email="psychologist@demo.local",
        password_hash="hash",
        full_name="Ирина Новикова",
        phone="+79001234567",
        role=UserRole.PSYCHOLOGIST,
        about_md="",
    )

    q1 = Question(
        id=1,
        key="remote_ready",
        text="Готовы ли работать удаленно?",
        question_type=QuestionType.YES_NO,
        required=True,
        weight=1.0,
    )
    q2 = Question(
        id=2,
        key="interest",
        text="Что ближе?",
        question_type=QuestionType.SINGLE_CHOICE,
        required=True,
        options_json=[
            {"label": "IT", "value": "it", "score": 3},
            {"label": "Маркетинг", "value": "marketing", "score": 2},
        ],
        weight=1.0,
    )
    section = SurveySection(id=1, title="Блок 1", position=1, questions=[q1, q2])

    test = SurveyTest(
        id=5,
        psychologist_id=psychologist.id,
        title="ПрофДНК: демо",
        description="Тестовый шаблон",
        share_token="demo-token",
        psychologist=psychologist,
        sections=[section],
        required_client_fields={
            "required_builtin_fields": ["full_name", "email"],
            "custom_fields": [
                {
                    "key": "city",
                    "label": "Город",
                    "type": "text",
                    "required": False,
                    "placeholder": "",
                }
            ],
            "report_templates": {
                "client": ["profile", "summary_metrics", "answers"],
                "psychologist": [
                    "profile",
                    "summary_metrics",
                    "charts",
                    "derived_metrics",
                    "answers",
                ],
            },
        },
    )

    answers = [
        Answer(question_id=1, question=q1, value_json=True),
        Answer(question_id=2, question=q2, value_json="it"),
    ]
    submission = Submission(
        id=99,
        test=test,
        test_id=test.id,
        client_full_name="Клиент Тестов",
        client_email="client@example.com",
        client_phone="+79990000000",
        client_extra_json={"custom_fields": {"city": "Москва"}},
        submitted_at=datetime(2026, 3, 21, 10, 30, tzinfo=timezone.utc),
        metrics_json={
            "total_score": 4.0,
            "max_score": 5.0,
            "score_percent": 80.0,
            "completion_percent": 100.0,
            "answered_count": 2,
            "total_questions": 2,
            "derived_metrics": [
                {
                    "key": "focus",
                    "label": "Фокус",
                    "expression": "total_score / max_score",
                    "description": "Отношение набранного к максимуму",
                    "value": 0.8,
                    "status": "ok",
                }
            ],
        },
        answers=answers,
    )
    return test, submission


def test_build_report_context_respects_templates() -> None:
    test, submission = _build_report_test_case()

    client_context = build_report_context(test, submission, report_kind="client")
    psych_context = build_report_context(test, submission, report_kind="psychologist")

    assert client_context["title"] == "Клиентский отчёт"
    assert psych_context["title"] == "Отчёт для профориентолога"
    assert client_context["report_block_keys"] == ["profile", "summary_metrics", "answers"]
    assert psych_context["report_block_keys"] == [
        "profile",
        "summary_metrics",
        "charts",
        "derived_metrics",
        "answers",
    ]
    assert len(client_context["answers"]) == 2
    assert any(item["label"] == "Заполнение теста" for item in psych_context["chart_items"])


def test_render_html_and_docx_reports() -> None:
    test, submission = _build_report_test_case()
    psych_context = build_report_context(test, submission, report_kind="psychologist")

    html = render_html_report(psych_context, report_kind="psychologist")
    assert "Отчёт для профориентолога" in html
    assert "Клиент Тестов" in html
    assert "Фокус" in html

    docx_buffer = build_docx_report(psych_context, report_kind="psychologist")
    payload = docx_buffer.getvalue()
    assert payload.startswith(b"PK")
    assert len(payload) > 1200
