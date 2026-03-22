from __future__ import annotations

from io import BytesIO

import qrcode
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.dependencies import get_optional_user, require_csrf_token, require_psychologist_or_admin
from app.models import Answer, InviteLink, QuestionType, Submission, Test, TestSection, User, UserRole
from app.services.client_fields import build_client_form_fields, normalize_client_fields_config
from app.services.content import render_safe_markdown
from app.services.email import send_client_report_email
from app.services.invite_links import (
    is_invite_link_available,
    is_invite_link_exhausted,
    is_invite_link_expired,
    is_invite_link_pending,
)
from app.services.logic import evaluate_condition
from app.services.rate_limit import check_request_rate_limit
from app.services.reports import build_docx_report, build_report_context, render_html_report
from app.services.scoring import calculate_metrics
from app.services.seed import DEMO_PSYCHOLOGIST_EMAIL, ensure_demo_showcase_data
from app.services.test_changes import log_test_change
from app.web import templates

router = APIRouter(tags=["public"])


def _is_empty(value: object) -> bool:
    return value is None or value == "" or (isinstance(value, list) and len(value) == 0)


def _load_test_for_client(test_id: int, db: Session) -> Test | None:
    return db.scalar(
        select(Test)
        .where(Test.id == test_id)
        .options(
            selectinload(Test.psychologist),
            selectinload(Test.sections).selectinload(TestSection.questions),
            selectinload(Test.formulas),
        )
    )


def _get_test_by_token(token: str, db: Session) -> tuple[Test, InviteLink | None]:
    invite_link = db.scalar(select(InviteLink).where(InviteLink.token == token))
    if invite_link:
        if not is_invite_link_available(invite_link):
            if invite_link.is_active and (
                is_invite_link_exhausted(invite_link) or is_invite_link_expired(invite_link)
            ):
                invite_link.is_active = False
                db.commit()
            if is_invite_link_pending(invite_link):
                raise HTTPException(
                    status_code=404,
                    detail="Ссылка ещё не активна. Попробуйте позже.",
                )
            if is_invite_link_expired(invite_link):
                raise HTTPException(status_code=404, detail="Срок действия ссылки истёк")
            raise HTTPException(status_code=404, detail="Ссылка для прохождения недоступна")
        test = _load_test_for_client(invite_link.test_id, db)
    else:
        test_id = db.scalar(select(Test.id).where(Test.share_token == token))
        test = _load_test_for_client(test_id, db) if test_id else None

    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")
    return test, invite_link


def _load_demo_story(db: Session) -> dict[str, object] | None:
    demo_psychologist = db.scalar(select(User).where(User.email == DEMO_PSYCHOLOGIST_EMAIL))
    if demo_psychologist is None:
        return None

    demo_test = db.scalar(
        select(Test)
        .where(Test.psychologist_id == demo_psychologist.id)
        .order_by(Test.created_at.asc())
        .options(selectinload(Test.invite_links), selectinload(Test.submissions))
    )
    if demo_test is None:
        return None

    submissions = sorted(demo_test.submissions, key=lambda row: row.submitted_at, reverse=True)
    latest_submission = submissions[0] if submissions else None
    named_links_count = len(demo_test.invite_links)
    submissions_count = len(submissions)

    return {
        "test_id": demo_test.id,
        "test_title": demo_test.title,
        "client_url": f"/t/{demo_test.share_token}",
        "test_detail_url": f"/tests/{demo_test.id}",
        "submissions_count": submissions_count,
        "named_links_count": named_links_count,
        "latest_submission_id": latest_submission.id if latest_submission else None,
        "psychologist_report_url": (
            f"/reports/{latest_submission.id}/psychologist.html" if latest_submission else None
        ),
        "client_report_url": (
            f"/reports/{latest_submission.id}/client.html"
            if latest_submission and demo_test.allow_client_report
            else None
        ),
        "is_ready": submissions_count >= 3 and named_links_count >= 2,
    }


def _build_tz_coverage_checklist(demo_story: dict[str, object] | None) -> list[dict[str, object]]:
    demo_ready = bool(demo_story and demo_story.get("is_ready"))
    test_detail_url = demo_story.get("test_detail_url") if demo_story else None
    return [
        {
            "title": "Роли и доступ",
            "description": "Админ создает психологов, управляет сроком доступа и блокировками.",
            "done": True,
            "url": "/admin",
        },
        {
            "title": "Конструктор методик",
            "description": "Психолог собирает тест в конструкторе, поддержан импорт JSON.",
            "done": True,
            "url": "/tests/new",
        },
        {
            "title": "Прохождение по ссылке без регистрации",
            "description": "Клиент открывает уникальный URL, заполняет поля и проходит тест онлайн.",
            "done": True,
            "url": demo_story.get("client_url") if demo_story else None,
        },
        {
            "title": "Результаты и метрики в системе",
            "description": "Сохранение прохождений + сравнение кампаний + аналитика на странице теста.",
            "done": True,
            "url": test_detail_url,
        },
        {
            "title": "Два вида отчетов (HTML и DOCX)",
            "description": "Отчеты для клиента и профориентолога формируются в реальном времени.",
            "done": True,
            "url": test_detail_url,
        },
        {
            "title": "Быстрый демо-пакет для защиты",
            "description": "Одна кнопка подготавливает демонстрационные данные и шаги презентации.",
            "done": demo_ready,
            "url": "/features#demo-scenario",
        },
    ]


@router.get("/features")
def features_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> object:
    demo_story = _load_demo_story(db)
    can_prepare_demo = bool(user and user.role in {UserRole.ADMIN, UserRole.PSYCHOLOGIST})
    tz_checklist = _build_tz_coverage_checklist(demo_story)
    return templates.TemplateResponse(
        request,
        "features.html",
        {
            "title": "О сайте",
            "user": user,
            "can_prepare_demo": can_prepare_demo,
            "demo_story": demo_story,
            "tz_checklist": tz_checklist,
        },
    )


@router.post("/features/demo/bootstrap")
def bootstrap_demo_showcase(
    _: None = Depends(require_csrf_token),
    _current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    payload = ensure_demo_showcase_data(db, target_submissions=3)
    return RedirectResponse(
        f"/features?notice=demo_showcase_ready&notice_type=success&demo_test_id={payload['test_id']}",
        status_code=303,
    )


@router.get("/guide/psychologist")
def psychologist_guide_page(
    request: Request,
    user: User | None = Depends(get_optional_user),
) -> object:
    return templates.TemplateResponse(
        request,
        "psychologist_guide.html",
        {
            "title": "Инструкция психолога",
            "user": user,
        },
    )


@router.get("/public/psychologists/{psychologist_id}")
def psychologist_business_card(
    psychologist_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> object:
    psychologist = db.get(User, psychologist_id)
    if not psychologist:
        raise HTTPException(status_code=404, detail="Психолог не найден")
    about_html = render_safe_markdown(psychologist.about_md or "")
    card_url = f"{settings.base_url}/public/psychologists/{psychologist.id}"
    return templates.TemplateResponse(
        request,
        "business_card.html",
        {
            "title": f"Визитка: {psychologist.full_name}",
            "psychologist": psychologist,
            "about_html": about_html,
            "card_url": card_url,
        },
    )


@router.get("/public/psychologists/{psychologist_id}/qr")
def business_card_qr(psychologist_id: int, db: Session = Depends(get_db)) -> Response:
    psychologist = db.get(User, psychologist_id)
    if not psychologist:
        raise HTTPException(status_code=404, detail="Психолог не найден")
    target_url = f"{settings.base_url}/public/psychologists/{psychologist.id}"
    image = qrcode.make(target_url)
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return Response(content=buffer.read(), media_type="image/png")


@router.get("/t/{token}")
def client_test_page(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
) -> object:
    test, invite_link = _get_test_by_token(token, db)
    client_profile_fields = build_client_form_fields(test.required_client_fields)
    return templates.TemplateResponse(
        request,
        "client_test.html",
        {
            "title": test.title,
            "test": test,
            "token": token,
            "invite_link": invite_link,
            "client_profile_fields": client_profile_fields,
        },
    )


@router.post("/t/{token}")
async def submit_client_test(
    token: str,
    request: Request,
    background_tasks: BackgroundTasks,
    _: None = Depends(require_csrf_token),
    db: Session = Depends(get_db),
) -> object:
    submit_rate_limit = check_request_rate_limit(
        request,
        scope="test_submit",
        limit=settings.submit_rate_limit_attempts,
        window_seconds=settings.submit_rate_limit_window_seconds,
        key_suffix=token,
    )
    if not submit_rate_limit.allowed:
        raise HTTPException(
            status_code=429,
            detail=(
                "Слишком много отправок анкеты. "
                f"Повторите через {submit_rate_limit.retry_after_seconds} сек."
            ),
            headers=submit_rate_limit.headers,
        )

    test, invite_link = _get_test_by_token(token, db)
    form = await request.form()

    client_full_name = str(form.get("client_full_name", "")).strip()
    client_email = str(form.get("client_email", "")).strip()
    client_phone = str(form.get("client_phone", "")).strip()
    client_age = str(form.get("client_age", "")).strip()

    if not client_full_name:
        raise HTTPException(status_code=400, detail="ФИО обязательно")
    if invite_link and invite_link.target_client_name:
        if client_full_name.lower() != invite_link.target_client_name.strip().lower():
            raise HTTPException(
                status_code=400,
                detail="Эта персональная ссылка предназначена для другого клиента",
            )

    client_fields_config = normalize_client_fields_config(test.required_client_fields)
    required_fields = set(client_fields_config["required_builtin_fields"])
    if "email" in required_fields and not client_email:
        raise HTTPException(status_code=400, detail="Email обязателен")
    if "phone" in required_fields and not client_phone:
        raise HTTPException(status_code=400, detail="Телефон обязателен")
    if "age" in required_fields and not client_age:
        raise HTTPException(status_code=400, detail="Возраст обязателен")

    custom_values: dict[str, str] = {}
    custom_fields = client_fields_config["custom_fields"]
    for field in custom_fields:
        key = str(field.get("key", "")).strip()
        label = str(field.get("label", "")).strip()
        if not key or not label:
            continue
        raw_value = str(form.get(f"client_custom_{key}", "")).strip()
        if field.get("required") and not raw_value:
            raise HTTPException(status_code=400, detail=f"Поле '{label}' обязательно")
        if raw_value:
            custom_values[key] = raw_value

    answer_map: dict[int, object] = {}
    answers_to_insert: list[Answer] = []
    answer_key_map: dict[str, object] = {}
    visible_question_ids: set[int] = set()
    visible_section_ids: set[int] = set()
    for section in test.sections:
        section_visible = evaluate_condition(section.visibility_condition_json, answer_key_map)
        if section_visible:
            visible_section_ids.add(section.id)
        for question in section.questions:
            field_name = f"q_{question.id}"
            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                value: object = form.getlist(field_name)
            elif question.question_type == QuestionType.YES_NO:
                raw_value = form.get(field_name)
                if raw_value in {None, ""}:
                    value = None
                else:
                    value = str(raw_value).lower() in {"true", "1", "yes", "on"}
            else:
                value = form.get(field_name)
            answer_map[question.id] = value
            answer_key_map[question.key] = value

    for section in test.sections:
        if section.id not in visible_section_ids:
            continue
        for question in section.questions:
            question_visible = evaluate_condition(question.visibility_condition_json, answer_key_map)
            if not question_visible:
                continue
            visible_question_ids.add(question.id)
            value = answer_map.get(question.id)
            if question.required and _is_empty(value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Заполните обязательный вопрос: {question.text}",
                )

    metrics_result = calculate_metrics(test, answer_map, visible_question_ids=visible_question_ids)

    client_extra: dict[str, object] = {}
    if client_age:
        client_extra["age"] = client_age
    if custom_values:
        client_extra["custom_fields"] = custom_values
    if invite_link:
        client_extra["invite_label"] = invite_link.label
        client_extra["invite_token"] = invite_link.token
        client_extra["invite_link_id"] = invite_link.id

    submission = Submission(
        test_id=test.id,
        client_full_name=client_full_name,
        client_email=client_email or None,
        client_phone=client_phone or None,
        client_extra_json=client_extra or None,
        score=metrics_result.total_score,
        metrics_json=metrics_result.as_metrics(),
    )
    db.add(submission)
    db.flush()

    for section in test.sections:
        for question in section.questions:
            if question.id not in visible_question_ids:
                continue
            answers_to_insert.append(
                Answer(
                    submission_id=submission.id,
                    question_id=question.id,
                    value_json=answer_map.get(question.id),
                )
            )
    db.add_all(answers_to_insert)

    if invite_link:
        invite_link.usage_count += 1
        if is_invite_link_exhausted(invite_link):
            invite_link.is_active = False

    log_test_change(
        db,
        test_id=test.id,
        action="client_submission_created",
        actor_user_id=None,
        details={
            "submission_id": submission.id,
            "invite_label": invite_link.label if invite_link else "Основная ссылка",
            "client_full_name": client_full_name,
        },
    )
    db.commit()

    public_token = test.share_token
    if client_email and test.allow_client_report:
        background_tasks.add_task(
            send_client_report_email,
            to_email=client_email,
            client_name=client_full_name,
            test_title=test.title,
            report_url=f"{settings.base_url}/t/{public_token}/report/{submission.id}.html",
        )

    return RedirectResponse(f"/t/{public_token}/done/{submission.id}", status_code=303)


@router.get("/t/{token}/done/{submission_id}")
def client_done_page(
    token: str,
    submission_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> object:
    test, _invite_link = _get_test_by_token(token, db)
    submission = db.scalar(
        select(Submission).where(Submission.id == submission_id, Submission.test_id == test.id)
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Результат не найден")
    return templates.TemplateResponse(
        request,
        "client_done.html",
        {
            "title": "Тест завершён",
            "test": test,
            "submission": submission,
            "token": token,
        },
    )


@router.get("/t/{token}/report/{submission_id}.html", response_class=HTMLResponse)
def client_report_html(
    token: str,
    submission_id: int,
    db: Session = Depends(get_db),
) -> HTMLResponse:
    test, _invite_link = _get_test_by_token(token, db)
    if not test.allow_client_report:
        raise HTTPException(status_code=403, detail="Клиентский отчёт отключён")
    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id, Submission.test_id == test.id)
        .options(
            selectinload(Submission.answers).selectinload(Answer.question),
            selectinload(Submission.test)
            .selectinload(Test.sections)
            .selectinload(TestSection.questions),
            selectinload(Submission.test).selectinload(Test.psychologist),
        )
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Результат не найден")
    context = build_report_context(test, submission, report_kind="client")
    return HTMLResponse(content=render_html_report(context, report_kind="client"))


@router.get("/t/{token}/report/{submission_id}.docx")
def client_report_docx(
    token: str,
    submission_id: int,
    db: Session = Depends(get_db),
) -> Response:
    test, _invite_link = _get_test_by_token(token, db)
    if not test.allow_client_report:
        raise HTTPException(status_code=403, detail="Клиентский отчёт отключён")
    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id, Submission.test_id == test.id)
        .options(
            selectinload(Submission.answers).selectinload(Answer.question),
            selectinload(Submission.test)
            .selectinload(Test.sections)
            .selectinload(TestSection.questions),
            selectinload(Submission.test).selectinload(Test.psychologist),
        )
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Результат не найден")

    context = build_report_context(test, submission, report_kind="client")
    buffer = build_docx_report(context, report_kind="client")
    headers = {
        "Content-Disposition": f'attachment; filename="client_report_{submission.id}.docx"'
    }
    return Response(
        content=buffer.read(),
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )

