from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, HTTPException, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies import get_optional_user, require_admin
from app.models import User, UserRole
from app.security import hash_password
from app.services.access_reminders import build_admin_access_expiry_reminders
from app.web import templates

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("")
def admin_page(
    request: Request,
    _: User = Depends(require_admin),
    current_user: User | None = Depends(get_optional_user),
    db: Session = Depends(get_db),
) -> object:
    psychologists = db.scalars(
        select(User).where(User.role == UserRole.PSYCHOLOGIST).order_by(User.created_at.desc())
    ).all()
    access_reminders = build_admin_access_expiry_reminders(psychologists)
    return templates.TemplateResponse(
        "admin.html",
        {
            "request": request,
            "title": "Админ",
            "user": current_user,
            "psychologists": psychologists,
            "access_reminders": access_reminders,
            "error": None,
        },
    )


@router.post("/psychologists")
def create_psychologist(
    request: Request,
    full_name: str = Form(...),
    email: str = Form(...),
    phone: str = Form(""),
    password: str = Form(...),
    access_until: str = Form(""),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    normalized_email = email.strip().lower()
    if db.scalar(select(User).where(User.email == normalized_email)):
        psychologists = db.scalars(
            select(User).where(User.role == UserRole.PSYCHOLOGIST).order_by(User.created_at.desc())
        ).all()
        access_reminders = build_admin_access_expiry_reminders(psychologists)
        return templates.TemplateResponse(
            "admin.html",
            {
                "request": request,
                "title": "Админ",
                "user": db.get(User, request.session.get("user_id")),
                "psychologists": psychologists,
                "access_reminders": access_reminders,
                "error": "Пользователь с таким email уже существует",
            },
            status_code=400,
        )

    access_until_dt = None
    if access_until.strip():
        try:
            access_until_dt = datetime.strptime(access_until.strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Неверный формат даты") from exc

    user = User(
        full_name=full_name.strip(),
        email=normalized_email,
        phone=phone.strip() or None,
        password_hash=hash_password(password),
        role=UserRole.PSYCHOLOGIST,
        access_until=access_until_dt,
    )
    db.add(user)
    db.commit()
    return RedirectResponse("/admin?notice=psychologist_created&notice_type=success", status_code=303)


@router.post("/psychologists/{psychologist_id}/toggle-block")
def toggle_block(
    psychologist_id: int,
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    user = db.get(User, psychologist_id)
    if not user or user.role != UserRole.PSYCHOLOGIST:
        raise HTTPException(status_code=404, detail="Psychologist not found")
    user.is_blocked = not user.is_blocked
    db.commit()
    return RedirectResponse(
        "/admin?notice=psychologist_block_toggled&notice_type=success",
        status_code=303,
    )


@router.post("/psychologists/{psychologist_id}/access")
def update_access(
    psychologist_id: int,
    access_until: str = Form(""),
    _: User = Depends(require_admin),
    db: Session = Depends(get_db),
) -> object:
    user = db.get(User, psychologist_id)
    if not user or user.role != UserRole.PSYCHOLOGIST:
        raise HTTPException(status_code=404, detail="Psychologist not found")

    if access_until.strip():
        try:
            user.access_until = datetime.strptime(access_until.strip(), "%Y-%m-%d").replace(
                tzinfo=timezone.utc
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="Неверный формат даты") from exc
    else:
        user.access_until = None
    db.commit()
    return RedirectResponse(
        "/admin?notice=psychologist_access_updated&notice_type=success",
        status_code=303,
    )
