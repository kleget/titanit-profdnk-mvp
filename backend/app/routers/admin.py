from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dependencies import get_optional_user, require_admin, require_csrf_token
from app.models import User, UserRole
from app.security import hash_password, validate_password_policy
from app.services.access_reminders import build_admin_access_expiry_reminders
from app.services.admin_audit import log_admin_action, recent_admin_audit_logs
from app.services.email import send_psychologist_welcome_email
from app.web import templates

router = APIRouter(prefix="/admin", tags=["admin"])


def _render_admin_page(
    request: Request,
    db: Session,
    *,
    current_user: User | None,
    error: str | None = None,
    form_values: dict[str, str] | None = None,
    status_code: int = 200,
) -> object:
    safe_form_values = form_values or {
        "full_name": "",
        "email": "",
        "phone": "",
        "access_until": "",
        "password": "",
    }
    psychologists = db.scalars(
        select(User).where(User.role == UserRole.PSYCHOLOGIST).order_by(User.created_at.desc())
    ).all()
    access_reminders = build_admin_access_expiry_reminders(psychologists)
    audit_logs = recent_admin_audit_logs(db, limit=40)
    return templates.TemplateResponse(
        request,
        "admin.html",
        {
            "title": "\u0410\u0434\u043c\u0438\u043d",
            "user": current_user,
            "psychologists": psychologists,
            "access_reminders": access_reminders,
            "audit_logs": audit_logs,
            "error": error,
            "form_values": safe_form_values,
        },
        status_code=status_code,
    )


@router.get("")
def admin_page(
    request: Request,
    _: User = Depends(require_admin),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> object:
    return _render_admin_page(
        request,
        db,
        current_user=current_user,
    )


@router.post("/psychologists")
def create_psychologist(
    request: Request,
    background_tasks: BackgroundTasks,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    password: str = Form(...),
    access_until: str = Form(""),
    __: None = Depends(require_csrf_token),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    current_user = db.get(User, request.session.get("user_id"))
    input_values = {
        "full_name": full_name.strip(),
        "email": email.strip(),
        "phone": phone.strip(),
        "access_until": access_until.strip(),
        "password": password,
    }
    normalized_email = email.strip().lower()
    password_error = validate_password_policy(password)
    if password_error:
        return _render_admin_page(
            request,
            db,
            current_user=current_user,
            error=password_error,
            form_values=input_values,
            status_code=400,
        )

    if db.scalar(select(User).where(User.email == normalized_email)):
        return _render_admin_page(
            request,
            db,
            current_user=current_user,
            error="Пользователь с таким email уже существует",
            form_values=input_values,
            status_code=400,
        )

    access_until_dt = None
    if access_until.strip():
        try:
            access_until_dt = datetime.strptime(access_until.strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError:
            return _render_admin_page(
                request,
                db,
                current_user=current_user,
                error="Неверный формат даты",
                form_values=input_values,
                status_code=400,
            )
    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        phone=phone.strip() or None,
        password_hash=hash_password(password),
        role=UserRole.PSYCHOLOGIST,
        access_until=access_until_dt,
    )
    db.add(user)
    db.flush()
    log_admin_action(
        db,
        admin_user_id=current_admin.id,
        action="psychologist_created",
        target_user_id=user.id,
        target_email=user.email,
        details={
            "full_name": user.full_name,
            "access_until": user.access_until.isoformat() if user.access_until else None,
        },
    )
    db.commit()
    background_tasks.add_task(
        send_psychologist_welcome_email,
        to_email=normalized_email,
        full_name=user.full_name,
        password=password,
        access_until=user.access_until,
        login_url=f"{settings.base_url}/login",
    )
    return RedirectResponse("/admin?notice=psychologist_created&notice_type=success", status_code=303)


@router.post("/psychologists/{psychologist_id}/toggle-block")
def toggle_block(
    psychologist_id: int,
    __: None = Depends(require_csrf_token),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    user = db.get(User, psychologist_id)
    if not user or user.role != UserRole.PSYCHOLOGIST:
        raise HTTPException(status_code=404, detail="Psychologist not found")
    user.is_blocked = not user.is_blocked
    log_admin_action(
        db,
        admin_user_id=current_admin.id,
        action="psychologist_blocked" if user.is_blocked else "psychologist_unblocked",
        target_user_id=user.id,
        target_email=user.email,
        details={"is_blocked": user.is_blocked},
    )
    db.commit()
    return RedirectResponse(
        "/admin?notice=psychologist_block_toggled&notice_type=success",
        status_code=303,
    )


@router.post("/psychologists/{psychologist_id}/access")
def update_access(
    psychologist_id: int,
    access_until: str = Form(""),
    __: None = Depends(require_csrf_token),
    current_admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    user = db.get(User, psychologist_id)
    if not user or user.role != UserRole.PSYCHOLOGIST:
        raise HTTPException(status_code=404, detail="Psychologist not found")

    previous_access_until = user.access_until.isoformat() if user.access_until else None
    if access_until.strip():
        try:
            user.access_until = datetime.strptime(access_until.strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Неверный формат даты") from exc
    else:
        user.access_until = None
    log_admin_action(
        db,
        admin_user_id=current_admin.id,
        action="psychologist_access_updated",
        target_user_id=user.id,
        target_email=user.email,
        details={
            "before": previous_access_until,
            "after": user.access_until.isoformat() if user.access_until else None,
        },
    )
    db.commit()
    return RedirectResponse(
        "/admin?notice=psychologist_access_updated&notice_type=success",
        status_code=303,
    )
