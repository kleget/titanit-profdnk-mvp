from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

import markdown
from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.dependencies import get_optional_user, require_psychologist_or_admin
from app.models import Answer, InviteLink, Submission, Test, TestSection, User, UserRole
from app.services.access_reminders import build_psychologist_access_reminder
from app.services.reports import build_docx_report, build_report_context, render_html_report
from app.services.scoring import calculate_metrics
from app.services.tests import (
    create_test_from_payload,
    export_test_config,
    formulas_from_flat_form,
    sections_from_flat_form,
)
from app.web import templates

router = APIRouter(tags=["psychologist"])


UPLOAD_DIR = Path(__file__).resolve().parents[1] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9а-яА-ЯёЁ_-]+", "_", value)
    return cleaned.strip("_")[:50] or "report"


def _ensure_test_access(test: Test, user: User) -> None:
    if user.role == UserRole.ADMIN:
        return
    if test.psychologist_id != user.id:
        raise HTTPException(status_code=404, detail="Test not found")


def _normalize_label(value: str) -> str:
    return " ".join(value.strip().split())


def _submission_invite_label(submission: Submission) -> str:
    extra = submission.client_extra_json or {}
    raw_value = extra.get("invite_label")
    if isinstance(raw_value, str):
        cleaned = _normalize_label(raw_value)
        if cleaned:
            return cleaned
    return "Default link"


def _build_invite_groups(submissions: list[Submission]) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for sub in submissions:
        label = _submission_invite_label(sub)
        if label not in grouped:
            grouped[label] = {
                "label": label,
                "count": 0,
                "last_submitted_at": sub.submitted_at,
            }
        grouped[label]["count"] = int(grouped[label]["count"]) + 1
        if sub.submitted_at > grouped[label]["last_submitted_at"]:
            grouped[label]["last_submitted_at"] = sub.submitted_at
    return sorted(
        grouped.values(),
        key=lambda item: (int(item["count"]), item["last_submitted_at"]),
        reverse=True,
    )


def _generate_unique_invite_token(db: Session) -> str:
    while True:
        token = secrets.token_urlsafe(24)
        invite_exists = db.scalar(select(InviteLink.id).where(InviteLink.token == token))
        test_exists = db.scalar(select(Test.id).where(Test.share_token == token))
        if not invite_exists and not test_exists:
            return token


@router.get("/")
def root_redirect(user: User | None = Depends(get_optional_user)) -> object:
    if not user:
        return RedirectResponse("/login", status_code=303)
    return RedirectResponse("/admin" if user.role == UserRole.ADMIN else "/dashboard", status_code=303)


@router.get("/dashboard")
def dashboard(
    request: Request,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    if current_user.role == UserRole.ADMIN:
        return RedirectResponse("/admin", status_code=303)

    tests_count = db.scalar(select(func.count(Test.id)).where(Test.psychologist_id == current_user.id)) or 0
    submissions_count = (
        db.scalar(
            select(func.count(Submission.id))
            .join(Test, Submission.test_id == Test.id)
            .where(Test.psychologist_id == current_user.id)
        )
        or 0
    )
    access_reminder = build_psychologist_access_reminder(current_user)
    about_html = markdown.markdown(current_user.about_md or "")
    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "title": "Личный кабинет",
            "user": current_user,
            "tests_count": tests_count,
            "submissions_count": submissions_count,
            "access_reminder": access_reminder,
            "about_html": about_html,
            "base_url": settings.base_url,
        },
    )


@router.post("/profile")
def update_profile(
    about_md: str = Form(""),
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Admin profile is not editable here")
    current_user.about_md = about_md
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)


@router.post("/profile/photo")
async def upload_photo(
    photo: UploadFile,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=400, detail="Admin photo upload is disabled")
    if not photo.filename:
        raise HTTPException(status_code=400, detail="File is empty")
    suffix = Path(photo.filename).suffix.lower()
    if suffix not in {".png", ".jpg", ".jpeg", ".webp"}:
        raise HTTPException(status_code=400, detail="Unsupported file type")
    file_name = f"{current_user.id}_{secrets.token_hex(6)}{suffix}"
    file_path = UPLOAD_DIR / file_name
    file_path.write_bytes(await photo.read())
    current_user.photo_filename = file_name
    db.commit()
    return RedirectResponse("/dashboard", status_code=303)


@router.get("/tests")
def tests_page(
    request: Request,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    query = select(Test).order_by(Test.created_at.desc()).options(selectinload(Test.submissions))
    if current_user.role == UserRole.PSYCHOLOGIST:
        query = query.where(Test.psychologist_id == current_user.id)
    tests = db.scalars(query).all()
    return templates.TemplateResponse(
        "tests.html",
        {
            "request": request,
            "title": "Мои опросники",
            "user": current_user,
            "tests": tests,
            "base_url": settings.base_url,
        },
    )


@router.get("/tests/new")
def new_test_page(
    request: Request,
    current_user: User = Depends(require_psychologist_or_admin),
) -> object:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin cannot create tests")
    return templates.TemplateResponse(
        "test_builder.html",
        {
            "request": request,
            "title": "Конструктор методик",
            "user": current_user,
        },
    )


@router.post("/tests/new/manual")
async def create_test_manual(
    request: Request,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin cannot create tests")

    form = await request.form()
    title = str(form.get("title", ""))
    description = str(form.get("description", ""))
    allow_client_report = str(form.get("allow_client_report", "false")).lower() == "true"
    required_client_fields = form.getlist("required_client_fields")

    sections = sections_from_flat_form(
        section_titles=form.getlist("section_titles[]"),
        question_texts=form.getlist("q_text[]"),
        question_types=form.getlist("q_type[]"),
        question_required=form.getlist("q_required[]"),
        question_options=form.getlist("q_options[]"),
        question_min=form.getlist("q_min[]"),
        question_max=form.getlist("q_max[]"),
        question_weight=form.getlist("q_weight[]"),
        question_section_titles=form.getlist("q_section[]"),
    )
    formulas = formulas_from_flat_form(
        metric_keys=form.getlist("metric_key[]"),
        metric_labels=form.getlist("metric_label[]"),
        metric_expressions=form.getlist("metric_expression[]"),
        metric_descriptions=form.getlist("metric_description[]"),
    )
    test = create_test_from_payload(
        db=db,
        psychologist_id=current_user.id,
        title=title,
        description=description,
        allow_client_report=allow_client_report,
        required_client_fields=required_client_fields,
        sections_payload=sections,
        formulas_payload=formulas,
    )
    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.post("/tests/new/import")
def create_test_import(
    title: str = Form(""),
    description: str = Form(""),
    allow_client_report: str = Form("true"),
    required_client_fields: list[str] = Form(default=[]),
    config_json: str = Form(...),
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    if current_user.role == UserRole.ADMIN:
        raise HTTPException(status_code=403, detail="Admin cannot create tests")
    try:
        parsed = json.loads(config_json)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON config") from exc
    sections = parsed.get("sections")
    if not isinstance(sections, list):
        raise HTTPException(status_code=400, detail="JSON must include sections[]")
    formulas = parsed.get("formula_metrics") or parsed.get("metric_formulas") or []
    if not isinstance(formulas, list):
        raise HTTPException(status_code=400, detail="JSON formula_metrics must be an array")
    test = create_test_from_payload(
        db=db,
        psychologist_id=current_user.id,
        title=(title or parsed.get("title") or "").strip(),
        description=(description or parsed.get("description") or "").strip(),
        allow_client_report=allow_client_report.lower() == "true",
        required_client_fields=required_client_fields
        or parsed.get("required_client_fields")
        or ["full_name"],
        sections_payload=sections,
        formulas_payload=formulas,
    )
    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.get("/tests/{test_id}")
def test_detail(
    test_id: int,
    request: Request,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    test = db.scalar(
        select(Test)
        .where(Test.id == test_id)
        .options(
            selectinload(Test.psychologist),
            selectinload(Test.sections).selectinload(TestSection.questions),
            selectinload(Test.formulas),
            selectinload(Test.invite_links),
            selectinload(Test.submissions).selectinload(Submission.answers),
        )
    )
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)

    submissions = sorted(test.submissions, key=lambda item: item.submitted_at, reverse=True)
    invite_groups = _build_invite_groups(submissions)
    return templates.TemplateResponse(
        "test_detail.html",
        {
            "request": request,
            "title": f"Тест: {test.title}",
            "user": current_user,
            "test": test,
            "submissions": submissions,
            "invite_groups": invite_groups,
            "base_url": settings.base_url,
        },
    )


@router.post("/tests/{test_id}/links")
def create_invite_link(
    test_id: int,
    label: str = Form(""),
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    test = db.scalar(select(Test).where(Test.id == test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)

    cleaned_label = _normalize_label(label)
    if not cleaned_label:
        raise HTTPException(status_code=400, detail="Link label is required")
    if len(cleaned_label) > 120:
        raise HTTPException(status_code=400, detail="Link label is too long")

    duplicate = db.scalar(
        select(InviteLink.id).where(InviteLink.test_id == test_id, InviteLink.label == cleaned_label)
    )
    if duplicate:
        raise HTTPException(status_code=400, detail="Link label already exists")

    invite_link = InviteLink(
        test_id=test.id,
        label=cleaned_label,
        token=_generate_unique_invite_token(db),
        is_active=True,
    )
    db.add(invite_link)
    db.commit()
    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.post("/tests/{test_id}/links/{link_id}/toggle")
def toggle_invite_link(
    test_id: int,
    link_id: int,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> object:
    test = db.scalar(select(Test).where(Test.id == test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)

    link = db.scalar(
        select(InviteLink).where(InviteLink.id == link_id, InviteLink.test_id == test_id)
    )
    if not link:
        raise HTTPException(status_code=404, detail="Invite link not found")

    link.is_active = not link.is_active
    db.commit()
    return RedirectResponse(f"/tests/{test.id}", status_code=303)


@router.get("/tests/{test_id}/submissions.json")
def submissions_json(
    test_id: int,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    test = db.scalar(select(Test).where(Test.id == test_id).options(selectinload(Test.submissions)))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)

    payload = [
        {
            "id": sub.id,
            "client_full_name": sub.client_full_name,
            "submitted_at": sub.submitted_at.isoformat(),
            "score": (sub.metrics_json or {}).get("total_score"),
            "completion_percent": (sub.metrics_json or {}).get("completion_percent"),
            "invite_label": _submission_invite_label(sub),
        }
        for sub in sorted(test.submissions, key=lambda item: item.submitted_at, reverse=True)
    ]
    return JSONResponse(payload)


@router.get("/tests/{test_id}/export.json")
def export_test(
    test_id: int,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    test = db.scalar(
        select(Test)
        .where(Test.id == test_id)
        .options(
            selectinload(Test.sections).selectinload(TestSection.questions),
            selectinload(Test.formulas),
        )
    )
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)
    return JSONResponse(export_test_config(test))


@router.get("/reports/{submission_id}/{report_kind}.html", response_class=HTMLResponse)
def report_html(
    submission_id: int,
    report_kind: str,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> HTMLResponse:
    if report_kind not in {"client", "psychologist"}:
        raise HTTPException(status_code=400, detail="Invalid report type")
    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.answers).selectinload(Answer.question),
            selectinload(Submission.test)
            .selectinload(Test.sections)
            .selectinload(TestSection.questions),
            selectinload(Submission.test).selectinload(Test.psychologist),
        )
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _ensure_test_access(submission.test, current_user)
    if report_kind == "client" and not submission.test.allow_client_report:
        raise HTTPException(status_code=403, detail="Client report disabled")

    context = build_report_context(submission.test, submission, report_kind=report_kind)  # type: ignore[arg-type]
    html = render_html_report(context, report_kind=report_kind)  # type: ignore[arg-type]
    return HTMLResponse(content=html)


@router.get("/reports/{submission_id}/{report_kind}.docx")
def report_docx(
    submission_id: int,
    report_kind: str,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    if report_kind not in {"client", "psychologist"}:
        raise HTTPException(status_code=400, detail="Invalid report type")
    submission = db.scalar(
        select(Submission)
        .where(Submission.id == submission_id)
        .options(
            selectinload(Submission.answers).selectinload(Answer.question),
            selectinload(Submission.test)
            .selectinload(Test.sections)
            .selectinload(TestSection.questions),
            selectinload(Submission.test).selectinload(Test.psychologist),
        )
    )
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    _ensure_test_access(submission.test, current_user)
    if report_kind == "client" and not submission.test.allow_client_report:
        raise HTTPException(status_code=403, detail="Client report disabled")

    context = build_report_context(submission.test, submission, report_kind=report_kind)  # type: ignore[arg-type]
    document = build_docx_report(context, report_kind=report_kind)  # type: ignore[arg-type]
    filename = _slugify(f"{submission.client_full_name}_{submission.id}_{report_kind}") + ".docx"
    headers = {"Content-Disposition": f'attachment; filename="{filename}"'}
    return StreamingResponse(
        document,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers,
    )


@router.get("/tests/{test_id}/stats")
def test_stats(
    test_id: int,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    test = db.scalar(select(Test).where(Test.id == test_id))
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)

    submissions_count = db.scalar(select(func.count(Submission.id)).where(Submission.test_id == test_id)) or 0
    latest_submission = db.scalar(
        select(Submission)
        .where(Submission.test_id == test_id)
        .order_by(Submission.submitted_at.desc())
        .limit(1)
    )
    return JSONResponse(
        {
            "submissions_count": submissions_count,
            "last_submitted_at": latest_submission.submitted_at.isoformat() if latest_submission else None,
        }
    )
