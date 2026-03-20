from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Question, QuestionType, Test, TestSection, User, UserRole
from app.security import hash_password


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def seed_initial_data(db: Session) -> None:
    admin = db.scalar(select(User).where(User.email == "admin@profdnk.local"))
    if not admin:
        admin = User(
            email="admin@profdnk.local",
            password_hash=hash_password("admin123"),
            full_name="Администратор Платформы",
            phone="+79990000000",
            role=UserRole.ADMIN,
            access_until=None,
            about_md="Системный администратор демо-стенда.",
        )
        db.add(admin)

    psychologist = db.scalar(select(User).where(User.email == "psychologist@demo.local"))
    if not psychologist:
        psychologist = User(
            email="psychologist@demo.local",
            password_hash=hash_password("demo12345"),
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
        title="ПрофДНК: базовая диагностика интересов",
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
    db.commit()

