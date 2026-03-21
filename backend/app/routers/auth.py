from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole, normalize_datetime
from app.security import verify_password
from app.config import settings
from app.services.rate_limit import check_request_rate_limit
from app.web import templates

router = APIRouter()


def _now() -> datetime:
    return datetime.now(timezone.utc)


@router.get("/login")
def login_page(request: Request) -> object:
    if request.session.get("user_id"):
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse(
        request,
        "login.html",
        {"title": "Вход", "error": None},
    )


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
) -> object:
    rate_limit = check_request_rate_limit(
        request,
        scope="login",
        limit=settings.login_rate_limit_attempts,
        window_seconds=settings.login_rate_limit_window_seconds,
    )
    if not rate_limit.allowed:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "title": "Вход",
                "error": (
                    "Слишком много попыток входа. "
                    f"Повторите через {rate_limit.retry_after_seconds} сек."
                ),
            },
            status_code=429,
            headers=rate_limit.headers,
        )

    user = db.scalar(select(User).where(User.email == email.strip().lower()))
    if not user or not verify_password(password, user.password_hash):
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": "Вход", "error": "Неверный логин или пароль"},
            status_code=400,
        )

    if user.is_blocked:
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": "Вход", "error": "Пользователь заблокирован"},
            status_code=403,
        )
    access_until = normalize_datetime(user.access_until)
    if access_until and access_until < _now():
        return templates.TemplateResponse(
            request,
            "login.html",
            {"title": "Вход", "error": "Срок доступа истёк"},
            status_code=403,
        )

    request.session["user_id"] = user.id
    redirect_to = "/admin" if user.role == UserRole.ADMIN else "/dashboard"
    return RedirectResponse(redirect_to, status_code=303)


@router.post("/logout")
def logout(request: Request) -> object:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
