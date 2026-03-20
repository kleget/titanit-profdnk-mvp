from __future__ import annotations

from io import BytesIO

import markdown
import qrcode
from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.models import Answer, QuestionType, Submission, Test, TestSection, User
from app.services.reports import build_docx_report, build_report_context, render_html_report
from app.services.scoring import calculate_metrics
from app.web import templates

router = APIRouter(tags=["public"])


def _is_empty(value: object) -> bool:
    return value is None or value == "" or (isinstance(value, list) and len(value) == 0)


def _get_test_by_token(token: str, db: Session) -> Test:
    test = db.scalar(
        select(Test)
        .where(Test.share_token == token)
        .options(
            selectinload(Test.psychologist),
            selectinload(Test.sections).selectinload(TestSection.questions),
        )
    )
    if not test:
        raise HTTPException(status_code=404, detail="Тест не найден")
    return test


@router.get("/public/psychologists/{psychologist_id}")
def psychologist_business_card(
    psychologist_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> object:
    psychologist = db.get(User, psychologist_id)
    if not psychologist:
        raise HTTPException(status_code=404, detail="Психолог не найден")
    about_html = markdown.markdown(psychologist.about_md or "")
    card_url = f"{settings.base_url}/public/psychologists/{psychologist.id}"
    return templates.TemplateResponse(
        "business_card.html",
        {
            "request": request,
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
    test = _get_test_by_token(token, db)
    return templates.TemplateResponse(
        "client_test.html",
        {
            "request": request,
            "title": test.title,
            "test": test,
            "token": token,
        },
    )


@router.post("/t/{token}")
async def submit_client_test(
    token: str,
    request: Request,
    db: Session = Depends(get_db),
) -> object:
    test = _get_test_by_token(token, db)
    form = await request.form()

    client_full_name = str(form.get("client_full_name", "")).strip()
    client_email = str(form.get("client_email", "")).strip()
    client_phone = str(form.get("client_phone", "")).strip()
    client_age = str(form.get("client_age", "")).strip()

    if not client_full_name:
        raise HTTPException(status_code=400, detail="ФИО обязательно")

    required_fields = test.required_client_fields or ["full_name"]
    if "email" in required_fields and not client_email:
        raise HTTPException(status_code=400, detail="Email обязателен")
    if "phone" in required_fields and not client_phone:
        raise HTTPException(status_code=400, detail="Телефон обязателен")
    if "age" in required_fields and not client_age:
        raise HTTPException(status_code=400, detail="Возраст обязателен")

    answer_map: dict[int, object] = {}
    answers_to_insert: list[Answer] = []
    for section in test.sections:
        for question in section.questions:
            field_name = f"q_{question.id}"
            if question.question_type == QuestionType.MULTIPLE_CHOICE:
                value: object = form.getlist(field_name)
            elif question.question_type == QuestionType.YES_NO:
                value = str(form.get(field_name, "")).lower() in {"true", "1", "yes", "on"}
            else:
                value = form.get(field_name)
            if question.required and _is_empty(value):
                raise HTTPException(
                    status_code=400,
                    detail=f"Заполните обязательный вопрос: {question.text}",
                )
            answer_map[question.id] = value

    metrics_result = calculate_metrics(test, answer_map)
    submission = Submission(
        test_id=test.id,
        client_full_name=client_full_name,
        client_email=client_email or None,
        client_phone=client_phone or None,
        client_extra_json={"age": client_age} if client_age else None,
        score=metrics_result.total_score,
        metrics_json=metrics_result.as_metrics(),
    )
    db.add(submission)
    db.flush()

    for section in test.sections:
        for question in section.questions:
            answers_to_insert.append(
                Answer(
                    submission_id=submission.id,
                    question_id=question.id,
                    value_json=answer_map.get(question.id),
                )
            )
    db.add_all(answers_to_insert)
    db.commit()

    return RedirectResponse(f"/t/{token}/done/{submission.id}", status_code=303)


@router.get("/t/{token}/done/{submission_id}")
def client_done_page(
    token: str,
    submission_id: int,
    request: Request,
    db: Session = Depends(get_db),
) -> object:
    test = _get_test_by_token(token, db)
    submission = db.scalar(select(Submission).where(Submission.id == submission_id, Submission.test_id == test.id))
    if not submission:
        raise HTTPException(status_code=404, detail="Результат не найден")
    return templates.TemplateResponse(
        "client_done.html",
        {
            "request": request,
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
    test = _get_test_by_token(token, db)
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
    test = _get_test_by_token(token, db)
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
