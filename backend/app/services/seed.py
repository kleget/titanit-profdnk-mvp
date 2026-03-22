from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.models import (
    Answer,
    InviteLink,
    MetricFormula,
    Question,
    QuestionType,
    Submission,
    Test,
    TestSection,
    User,
    UserRole,
)
from app.security import hash_password
from app.services.scoring import calculate_metrics


DEMO_ADMIN_EMAIL = "admin@profdnk.local"
DEMO_ADMIN_PASSWORD = "admin123"
DEMO_PSYCHOLOGIST_EMAIL = "psychologist@demo.local"
DEMO_PSYCHOLOGIST_PASSWORD = "demo12345"
DEMO_TEST_TITLE = "ПрофДНК: базовая диагностика интересов"


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seed_initial_data(db: Session) -> None:
    admin = db.scalar(select(User).where(User.email == DEMO_ADMIN_EMAIL))
    if not admin:
        admin = User(
            email=DEMO_ADMIN_EMAIL,
            password_hash=hash_password(DEMO_ADMIN_PASSWORD),
            full_name="Администратор Платформы",
            phone="+79990000000",
            role=UserRole.ADMIN,
            access_until=None,
            about_md="Системный администратор демо-стенда.",
        )
        db.add(admin)

    psychologist = db.scalar(select(User).where(User.email == DEMO_PSYCHOLOGIST_EMAIL))
    if not psychologist:
        psychologist = User(
            email=DEMO_PSYCHOLOGIST_EMAIL,
            password_hash=hash_password(DEMO_PSYCHOLOGIST_PASSWORD),
            full_name="Ирина Новикова",
            phone="+79001234567",
            role=UserRole.PSYCHOLOGIST,
            access_until=_utcnow() + timedelta(days=180),
            about_md=(
                "Практикующий профориентолог.\n\n"
                "Помогаю подросткам и взрослым выбрать траекторию развития."
            ),
        )
        db.add(psychologist)
        db.flush()

    existing_test = db.scalar(select(Test).where(Test.psychologist_id == psychologist.id))
    if existing_test:
        db.commit()
        return

    test = Test(
        psychologist_id=psychologist.id,
        title=DEMO_TEST_TITLE,
        description=(
            "Демо-методика для MVP. Содержит все обязательные типы вопросов и базовый подсчёт."
        ),
        share_token=secrets.token_urlsafe(12),
        required_client_fields=["full_name", "email", "phone", "age"],
        allow_client_report=True,
    )
    db.add(test)
    db.flush()

    intro = TestSection(test_id=test.id, title="Профиль клиента", position=1)
    prefs = TestSection(test_id=test.id, title="Интересы и стиль работы", position=2)
    db.add_all([intro, prefs])
    db.flush()

    questions = [
        Question(
            section_id=intro.id,
            key="motivation_text",
            text="Что для вас сейчас самая важная карьерная цель?",
            question_type=QuestionType.TEXTAREA,
            required=True,
            position=1,
            weight=1.0,
        ),
        Question(
            section_id=intro.id,
            key="experience_years",
            text="Сколько лет вы уже работаете (или учитесь по направлению)?",
            question_type=QuestionType.NUMBER,
            required=True,
            min_value=0,
            max_value=20,
            position=2,
            weight=1.2,
        ),
        Question(
            section_id=intro.id,
            key="learning_mode",
            text="Какой формат обучения вам ближе?",
            question_type=QuestionType.SINGLE_CHOICE,
            required=True,
            options_json=[
                {"label": "Практика на проектах", "value": "practice", "score": 3},
                {"label": "Курсы и лекции", "value": "courses", "score": 2},
                {"label": "Самостоятельно", "value": "self", "score": 1},
            ],
            position=3,
            weight=1.0,
        ),
        Question(
            section_id=prefs.id,
            key="work_values",
            text="Выберите, что для вас важно в работе",
            question_type=QuestionType.MULTIPLE_CHOICE,
            required=True,
            options_json=[
                {"label": "Доход", "value": "income", "score": 3},
                {"label": "Свобода графика", "value": "freedom", "score": 3},
                {"label": "Стабильность", "value": "stability", "score": 2},
                {"label": "Командная среда", "value": "team", "score": 2},
            ],
            position=1,
            weight=1.0,
        ),
        Question(
            section_id=prefs.id,
            key="ready_remote",
            text="Готовы ли вы работать удалённо?",
            question_type=QuestionType.YES_NO,
            required=True,
            position=2,
            weight=1.0,
        ),
        Question(
            section_id=prefs.id,
            key="stress_level",
            text="Оцените комфорт при высокой нагрузке (1-10)",
            question_type=QuestionType.SLIDER,
            required=True,
            min_value=1,
            max_value=10,
            position=3,
            weight=1.2,
        ),
        Question(
            section_id=prefs.id,
            key="digital_skill",
            text="Оцените цифровые навыки (1-5)",
            question_type=QuestionType.RATING,
            required=True,
            min_value=1,
            max_value=5,
            position=4,
            weight=1.0,
        ),
        Question(
            section_id=prefs.id,
            key="available_start",
            text="Когда готовы начать новый карьерный трек?",
            question_type=QuestionType.DATETIME,
            required=False,
            position=5,
            weight=1.0,
        ),
        Question(
            section_id=prefs.id,
            key="preferred_industry",
            text="Предпочитаемая сфера деятельности",
            question_type=QuestionType.TEXT,
            required=False,
            position=6,
            weight=1.0,
        ),
    ]
    db.add_all(questions)

    formulas = [
        MetricFormula(
            test_id=test.id,
            key="adaptability_index",
            label="Индекс адаптивности",
            expression="round((digital_skill + stress_level) / 2, 2)",
            description="Средняя оценка цифровых навыков и устойчивости к нагрузке.",
            position=1,
        ),
        MetricFormula(
            test_id=test.id,
            key="remote_readiness",
            label="Готовность к удалёнке",
            expression="ready_remote * 100",
            description="100, если клиент готов к удаленной работе.",
            position=2,
        ),
        MetricFormula(
            test_id=test.id,
            key="career_energy",
            label="Карьерная энергия",
            expression="round((experience_years + stress_level + digital_skill) / 3, 2)",
            description="Сводная метрика опыта и устойчивости к нагрузке.",
            position=3,
        ),
    ]
    db.add_all(formulas)
    db.commit()


def _generate_unique_invite_token(db: Session) -> str:
    while True:
        token = secrets.token_urlsafe(18)
        invite_exists = db.scalar(select(InviteLink.id).where(InviteLink.token == token))
        test_exists = db.scalar(select(Test.id).where(Test.share_token == token))
        if not invite_exists and not test_exists:
            return token


def _demo_answer_for_question(question: Question, sample_index: int) -> object:
    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        if not question.options_json:
            return []
        values = [
            str(option.get("value"))
            for option in question.options_json
            if isinstance(option, dict) and option.get("value") not in {None, ""}
        ]
        if not values:
            return []
        if len(values) == 1:
            return [values[0]]
        start = sample_index % len(values)
        second = (start + 1) % len(values)
        return [values[start], values[second]]

    if question.question_type == QuestionType.SINGLE_CHOICE:
        if not question.options_json:
            return ""
        values = [
            str(option.get("value"))
            for option in question.options_json
            if isinstance(option, dict) and option.get("value") not in {None, ""}
        ]
        if not values:
            return ""
        return values[sample_index % len(values)]

    if question.question_type == QuestionType.YES_NO:
        return sample_index % 2 == 0

    if question.question_type in {QuestionType.NUMBER, QuestionType.SLIDER, QuestionType.RATING}:
        min_value = question.min_value if question.min_value is not None else 1.0
        max_value = question.max_value if question.max_value is not None else min_value + 5.0
        if max_value < min_value:
            max_value = min_value
        span = max(max_value - min_value, 0.0)
        if span == 0:
            value = min_value
        else:
            step = min(sample_index, 4) / 4
            value = min_value + span * step
        rounded = round(value, 2)
        return int(rounded) if rounded.is_integer() else rounded

    if question.question_type == QuestionType.DATETIME:
        return (_utcnow() - timedelta(days=sample_index)).replace(microsecond=0).isoformat()

    if question.question_type == QuestionType.TEXTAREA:
        return (
            "Демо-ответ клиента для защиты.\n"
            f"Пример #{sample_index + 1}: мотивация и ожидания по карьерному треку."
        )

    return f"Демо-ответ #{sample_index + 1}"


def _build_demo_answer_map(test: Test, sample_index: int) -> tuple[dict[int, object], set[int]]:
    answer_map: dict[int, object] = {}
    visible_question_ids: set[int] = set()
    ordered_sections = sorted(test.sections, key=lambda section: section.position)
    for section in ordered_sections:
        ordered_questions = sorted(section.questions, key=lambda question: question.position)
        for question in ordered_questions:
            answer_map[question.id] = _demo_answer_for_question(question, sample_index)
            visible_question_ids.add(question.id)
    return answer_map, visible_question_ids


def _load_demo_test(db: Session) -> Test:
    psychologist = db.scalar(select(User).where(User.email == DEMO_PSYCHOLOGIST_EMAIL))
    if psychologist is None:
        raise RuntimeError("Demo psychologist is missing")

    demo_test = db.scalar(
        select(Test)
        .where(Test.psychologist_id == psychologist.id)
        .order_by(Test.created_at.asc())
        .options(
            selectinload(Test.sections).selectinload(TestSection.questions),
            selectinload(Test.formulas),
            selectinload(Test.invite_links),
            selectinload(Test.submissions),
        )
    )
    if demo_test is None:
        raise RuntimeError("Demo test is missing")
    return demo_test


def ensure_demo_showcase_data(db: Session, *, target_submissions: int = 3) -> dict[str, object]:
    seed_initial_data(db)
    demo_test = _load_demo_test(db)

    named_link_labels = ["School-234", "VK-Ads"]
    created_links = 0
    link_by_label: dict[str, InviteLink] = {link.label: link for link in demo_test.invite_links}
    for label in named_link_labels:
        if label in link_by_label:
            continue
        link = InviteLink(
            test_id=demo_test.id,
            label=label,
            token=_generate_unique_invite_token(db),
            is_active=True,
            usage_limit=None,
            usage_count=0,
        )
        db.add(link)
        db.flush()
        link_by_label[label] = link
        created_links += 1

    existing_submissions_count = (
        db.scalar(select(func.count(Submission.id)).where(Submission.test_id == demo_test.id)) or 0
    )
    to_create = max(0, target_submissions - existing_submissions_count)
    created_submissions = 0

    demo_clients: list[tuple[str, str, int, str | None]] = [
        ("Алина Смирнова", "alina.demo@example.com", 16, "School-234"),
        ("Максим Орлов", "max.demo@example.com", 20, "VK-Ads"),
        ("Наталья Воронцова", "nataly.demo@example.com", 28, None),
        ("Игорь Литвинов", "igor.demo@example.com", 24, "School-234"),
        ("Полина Громова", "polina.demo@example.com", 31, "VK-Ads"),
    ]

    for offset in range(to_create):
        sample_index = existing_submissions_count + offset
        base_name, base_email, age, source_label = demo_clients[sample_index % len(demo_clients)]
        full_name = f"{base_name} #{sample_index + 1}"
        email = base_email.replace("@", f"+{sample_index + 1}@")

        answer_map, visible_question_ids = _build_demo_answer_map(demo_test, sample_index)
        metrics_result = calculate_metrics(
            demo_test,
            answer_map,
            visible_question_ids=visible_question_ids,
        )

        client_extra: dict[str, object] = {"age": str(age)}
        invite_link = link_by_label.get(source_label or "")
        if invite_link is not None:
            client_extra["invite_label"] = invite_link.label
            client_extra["invite_link_id"] = invite_link.id
            client_extra["invite_token"] = invite_link.token
            invite_link.usage_count += 1
        else:
            client_extra["invite_label"] = "Основная ссылка"

        submission = Submission(
            test_id=demo_test.id,
            client_full_name=full_name,
            client_email=email,
            client_phone=f"+7900{sample_index + 1000000:07d}",
            client_extra_json=client_extra,
            score=metrics_result.total_score,
            metrics_json=metrics_result.as_metrics(),
            submitted_at=_utcnow() - timedelta(minutes=(to_create - offset) * 11),
        )
        db.add(submission)
        db.flush()

        answers_to_insert: list[Answer] = []
        for question_id in visible_question_ids:
            answers_to_insert.append(
                Answer(
                    submission_id=submission.id,
                    question_id=question_id,
                    value_json=answer_map.get(question_id),
                )
            )
        db.add_all(answers_to_insert)
        created_submissions += 1

    db.commit()

    refreshed_test = _load_demo_test(db)
    submissions_sorted = sorted(
        refreshed_test.submissions,
        key=lambda submission: submission.submitted_at,
        reverse=True,
    )
    latest_submission = submissions_sorted[0] if submissions_sorted else None

    return {
        "test_id": refreshed_test.id,
        "share_token": refreshed_test.share_token,
        "named_links_count": len(refreshed_test.invite_links),
        "submissions_count": len(refreshed_test.submissions),
        "latest_submission_id": latest_submission.id if latest_submission else None,
        "created_links_count": created_links,
        "created_submissions_count": created_submissions,
    }
