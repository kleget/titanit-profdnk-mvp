from __future__ import annotations

import json
import re
import secrets
from pathlib import Path

from fastapi import APIRouter, Depends, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session, selectinload

from app.config import settings
from app.db import get_db
from app.dependencies import get_optional_user, require_psychologist_or_admin
from app.models import Answer, InviteLink, Submission, Test, TestSection, User, UserRole
from app.services.access_reminders import build_psychologist_access_reminder
from app.services.content import render_safe_markdown
from app.services.invite_links import (
    INVITE_LINK_STATE_ACTIVE,
    INVITE_LINK_STATE_UNKNOWN,
    invite_link_limit_text,
    invite_link_state,
    invite_link_state_label,
    is_invite_link_exhausted,
)
from app.services.reports import build_docx_report, build_report_context, render_html_report
from app.services.tests import (
    custom_client_fields_from_flat_form,
    create_test_from_payload,
    export_test_config,
    formulas_from_flat_form,
    report_templates_from_flat_form,
    sections_from_flat_form,
)
from app.web import templates

router = APIRouter(tags=["psychologist"])


UPLOAD_DIR = Path(__file__).resolve().parents[1] / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def _slugify(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
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
    return "Основная ссылка"


def _submission_invite_link_id(submission: Submission) -> int | None:
    extra = submission.client_extra_json or {}
    raw_value = extra.get("invite_link_id")
    if isinstance(raw_value, int):
        return raw_value
    if isinstance(raw_value, str) and raw_value.isdigit():
        return int(raw_value)
    return None


def _parse_usage_limit(raw_value: str) -> int | None:
    cleaned = raw_value.strip()
    if not cleaned:
        return None
    try:
        parsed = int(cleaned)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Лимит прохождений должен быть целым числом") from exc
    if parsed <= 0:
        raise HTTPException(status_code=400, detail="Лимит прохождений должен быть больше нуля")
    if parsed > 1_000_000:
        raise HTTPException(status_code=400, detail="Лимит прохождений слишком большой")
    return parsed


def _build_invite_link_maps(test: Test) -> tuple[dict[int, InviteLink], dict[str, InviteLink]]:
    by_id: dict[int, InviteLink] = {}
    by_label: dict[str, InviteLink] = {}
    for link in test.invite_links:
        by_id[link.id] = link
        by_label[link.label] = link
    return by_id, by_label


def _submission_invite_state(submission: Submission, invite_links_by_id: dict[int, InviteLink]) -> str:
    invite_link_id = _submission_invite_link_id(submission)
    if invite_link_id is None:
        return INVITE_LINK_STATE_ACTIVE
    link = invite_links_by_id.get(invite_link_id)
    if not link:
        return INVITE_LINK_STATE_UNKNOWN
    return invite_link_state(link)


def _submission_invite_limit_text(
    submission: Submission, invite_links_by_id: dict[int, InviteLink]
) -> str:
    invite_link_id = _submission_invite_link_id(submission)
    if invite_link_id is None:
        return "без лимита"
    link = invite_links_by_id.get(invite_link_id)
    if not link:
        return "-"
    return invite_link_limit_text(link)


def _submission_rows_for_template(
    submissions: list[Submission],
    invite_links_by_id: dict[int, InviteLink],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for submission in submissions:
        state = _submission_invite_state(submission, invite_links_by_id)
        rows.append(
            {
                "submission": submission,
                "invite_label": _submission_invite_label(submission),
                "invite_state": state,
                "invite_state_label": invite_link_state_label(state),
            }
        )
    return rows


def _build_invite_groups(
    submissions: list[Submission],
    invite_links_by_label: dict[str, InviteLink],
) -> list[dict[str, object]]:
    grouped: dict[str, dict[str, object]] = {}
    for sub in submissions:
        label = _submission_invite_label(sub)
        state = INVITE_LINK_STATE_ACTIVE
        limit_text = "без лимита"
        if label != "Основная ссылка":
            link = invite_links_by_label.get(label)
            if link:
                state = invite_link_state(link)
                limit_text = invite_link_limit_text(link)
            else:
                state = INVITE_LINK_STATE_UNKNOWN
                limit_text = "-"
        if label not in grouped:
            grouped[label] = {
                "label": label,
                "count": 0,
                "last_submitted_at": sub.submitted_at,
                "link_state": state,
                "link_state_label": invite_link_state_label(state),
                "link_limit_text": limit_text,
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
    about_html = render_safe_markdown(current_user.about_md or "")
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {
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
    return RedirectResponse("/dashboard?notice=profile_saved&notice_type=success", status_code=303)


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
    return RedirectResponse("/dashboard?notice=photo_uploaded&notice_type=success", status_code=303)


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
        request,
        "tests.html",
        {
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
        request,
        "test_builder.html",
        {
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
    custom_client_fields = custom_client_fields_from_flat_form(
        field_keys=form.getlist("cf_key[]"),
        field_labels=form.getlist("cf_label[]"),
        field_types=form.getlist("cf_type[]"),
        field_required=form.getlist("cf_required[]"),
        field_placeholders=form.getlist("cf_placeholder[]"),
    )
    report_templates = report_templates_from_flat_form(
        client_blocks=form.getlist("rt_client[]"),
        psychologist_blocks=form.getlist("rt_psychologist[]"),
    )

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
        custom_client_fields=custom_client_fields,
        report_templates=report_templates,
        sections_payload=sections,
        formulas_payload=formulas,
    )
    return RedirectResponse(
        f"/tests/{test.id}?notice=test_created&notice_type=success",
        status_code=303,
    )


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
    parsed_client_fields = parsed.get("client_fields")
    if not isinstance(parsed_client_fields, dict):
        parsed_client_fields = {}
    custom_client_fields = (
        parsed.get("custom_client_fields")
        or parsed_client_fields.get("custom_fields")
        or []
    )
    if not isinstance(custom_client_fields, list):
        raise HTTPException(status_code=400, detail="JSON custom_client_fields must be an array")
    report_templates = parsed.get("report_templates")
    if report_templates is not None and not isinstance(report_templates, dict):
        raise HTTPException(status_code=400, detail="JSON report_templates must be an object")

    test = create_test_from_payload(
        db=db,
        psychologist_id=current_user.id,
        title=(title or parsed.get("title") or "").strip(),
        description=(description or parsed.get("description") or "").strip(),
        allow_client_report=allow_client_report.lower() == "true",
        required_client_fields=required_client_fields
        or parsed.get("required_client_fields")
        or parsed_client_fields.get("required_builtin_fields")
        or ["full_name"],
        custom_client_fields=custom_client_fields,
        report_templates=report_templates,
        sections_payload=sections,
        formulas_payload=formulas,
    )
    return RedirectResponse(
        f"/tests/{test.id}?notice=test_imported&notice_type=success",
        status_code=303,
    )


@router.get("/tests/{test_id}")
def test_detail(
    test_id: int,
    request: Request,
    source_status: str = "all",
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

    links_were_updated = False
    for link in test.invite_links:
        if link.is_active and is_invite_link_exhausted(link):
            link.is_active = False
            links_were_updated = True
    if links_were_updated:
        db.commit()

    submissions = sorted(test.submissions, key=lambda item: item.submitted_at, reverse=True)
    invite_links_by_id, invite_links_by_label = _build_invite_link_maps(test)
    invite_groups = _build_invite_groups(submissions, invite_links_by_label)
    submission_rows = _submission_rows_for_template(submissions, invite_links_by_id)
    allowed_filters = {"all", "active", "exhausted", "disabled", "unknown"}
    if source_status not in allowed_filters:
        source_status = "all"
    if source_status != "all":
        submission_rows = [row for row in submission_rows if row["invite_state"] == source_status]

    invite_link_rows = []
    for link in test.invite_links:
        state = invite_link_state(link)
        invite_link_rows.append(
            {
                "link": link,
                "state": state,
                "state_label": invite_link_state_label(state),
                "limit_text": invite_link_limit_text(link),
            }
        )

    return templates.TemplateResponse(
        request,
        "test_detail.html",
        {
            "title": f"Тест: {test.title}",
            "user": current_user,
            "test": test,
            "submission_rows": submission_rows,
            "invite_groups": invite_groups,
            "invite_link_rows": invite_link_rows,
            "source_status_filter": source_status,
            "base_url": settings.base_url,
        },
    )


@router.post("/tests/{test_id}/links")
def create_invite_link(
    test_id: int,
    label: str = Form(""),
    usage_limit: str = Form(""),
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

    parsed_usage_limit = _parse_usage_limit(usage_limit)
    invite_link = InviteLink(
        test_id=test.id,
        label=cleaned_label,
        token=_generate_unique_invite_token(db),
        is_active=True,
        usage_limit=parsed_usage_limit,
    )
    db.add(invite_link)
    db.commit()
    return RedirectResponse(
        f"/tests/{test.id}?notice=invite_link_added&notice_type=success",
        status_code=303,
    )


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

    if not link.is_active and is_invite_link_exhausted(link):
        raise HTTPException(status_code=400, detail="Ссылка исчерпала лимит прохождений")

    link.is_active = not link.is_active
    db.commit()
    return RedirectResponse(
        f"/tests/{test.id}?notice=invite_link_toggled&notice_type=success",
        status_code=303,
    )


@router.get("/tests/{test_id}/submissions.json")
def submissions_json(
    test_id: int,
    current_user: User = Depends(require_psychologist_or_admin),
    db: Session = Depends(get_db),
) -> JSONResponse:
    test = db.scalar(
        select(Test)
        .where(Test.id == test_id)
        .options(selectinload(Test.submissions), selectinload(Test.invite_links))
    )
    if not test:
        raise HTTPException(status_code=404, detail="Test not found")
    _ensure_test_access(test, current_user)

    links_were_updated = False
    for link in test.invite_links:
        if link.is_active and is_invite_link_exhausted(link):
            link.is_active = False
            links_were_updated = True
    if links_were_updated:
        db.commit()

    invite_links_by_id, _invite_links_by_label = _build_invite_link_maps(test)
    payload = []
    for sub in sorted(test.submissions, key=lambda item: item.submitted_at, reverse=True):
        state = _submission_invite_state(sub, invite_links_by_id)
        payload.append(
            {
                "id": sub.id,
                "client_full_name": sub.client_full_name,
                "submitted_at": sub.submitted_at.isoformat(),
                "score": (sub.metrics_json or {}).get("total_score"),
                "completion_percent": (sub.metrics_json or {}).get("completion_percent"),
                "invite_label": _submission_invite_label(sub),
                "invite_state": state,
                "invite_state_label": invite_link_state_label(state),
                "invite_limit_text": _submission_invite_limit_text(sub, invite_links_by_id),
            }
        )
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
