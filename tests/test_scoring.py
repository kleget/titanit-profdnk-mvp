from __future__ import annotations

from app.models import MetricFormula, Question, QuestionType, Test as SurveyTest
from app.models import TestSection as SurveySection
from app.services.scoring import calculate_metrics


def _build_scoring_test_case() -> tuple[SurveyTest, dict[int, object]]:
    q_remote = Question(
        id=1,
        key="remote_ready",
        text="Готовы ли вы работать удалённо?",
        question_type=QuestionType.YES_NO,
        required=True,
        weight=2.0,
    )
    q_interest = Question(
        id=2,
        key="interest",
        text="Выберите приоритет",
        question_type=QuestionType.SINGLE_CHOICE,
        required=True,
        weight=1.5,
        options_json=[
            {"label": "Дизайн", "value": "design", "score": 3},
            {"label": "Аналитика", "value": "analytics", "score": 2},
            {"label": "Продажи", "value": "sales", "score": 1},
        ],
    )
    q_comfort = Question(
        id=3,
        key="comfort",
        text="Комфорт при высокой нагрузке",
        question_type=QuestionType.SLIDER,
        required=True,
        min_value=0,
        max_value=10,
        weight=4.0,
    )
    q_comment = Question(
        id=4,
        key="comment",
        text="Комментарий",
        question_type=QuestionType.TEXTAREA,
        required=False,
        weight=1.0,
    )

    section = SurveySection(
        id=1,
        title="Профиль",
        position=1,
        questions=[q_remote, q_interest, q_comfort, q_comment],
    )

    formulas = [
        MetricFormula(
            id=1,
            key="fit_index",
            label="Индекс соответствия",
            expression="round((total_score / max_score) * 100, 2)",
            description="Нормированный индекс по набранным баллам",
            position=1,
        ),
        MetricFormula(
            id=2,
            key="risk_flag",
            label="Проверка рисков",
            expression="unknown_var + 1",
            description="Специальная формула для проверки обработки ошибок",
            position=2,
        ),
    ]

    test = SurveyTest(
        id=1,
        psychologist_id=10,
        title="Демо методика",
        description="Тест для проверки scoring",
        share_token="token123",
        required_client_fields=["full_name"],
        sections=[section],
        formulas=formulas,
    )

    answer_map: dict[int, object] = {
        1: True,
        2: "design",
        3: 7,
        4: "Хочу проектную работу",
    }
    return test, answer_map


def test_calculate_metrics_computes_expected_values() -> None:
    test, answer_map = _build_scoring_test_case()
    result = calculate_metrics(test, answer_map)
    metrics = result.as_metrics()

    assert result.total_questions == 4
    assert result.answered_count == 4
    assert round(result.total_score, 2) == 9.30
    assert round(result.max_score, 2) == 10.50
    assert round(result.completion_percent, 2) == 100.00
    assert round(metrics["score_percent"], 2) == 88.57
    assert metrics["formula_context"]["interest"] == 3.0
    assert metrics["formula_context"]["interest_score"] == 4.5

    derived = metrics["derived_metrics"]
    assert derived[0]["key"] == "fit_index"
    assert derived[0]["status"] == "ok"
    assert round(float(derived[0]["value"]), 2) == 88.57
    assert derived[1]["key"] == "risk_flag"
    assert derived[1]["status"] == "error"
    assert "Unknown variable" in derived[1]["error"]


def test_calculate_metrics_tracks_completion_for_partial_answers() -> None:
    test, answer_map = _build_scoring_test_case()
    partial_answers = {1: True, 2: "analytics"}

    result = calculate_metrics(test, partial_answers)

    assert result.answered_count == 2
    assert result.total_questions == 4
    assert round(result.completion_percent, 2) == 50.00
    assert result.total_score > 0
    assert result.max_score > result.total_score
