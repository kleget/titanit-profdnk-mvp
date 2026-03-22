from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_db
from app.dependencies import require_csrf_token
from app.models import User, UserRole, normalize_datetime
from app.security import verify_password
from app.services.csrf import rotate_csrf_token
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
        {"title": "\u0412\u0445\u043e\u0434", "error": None},
    )


@router.post("/login")
def login(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    _: None = Depends(require_csrf_token),
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
                "title": "\u0412\u0445\u043e\u0434",
                "error": (
                    "\u0421\u043b\u0438\u0448\u043a\u043e\u043c \u043c\u043d\u043e\u0433\u043e "
                    "\u043f\u043e\u043f\u044b\u0442\u043e\u043a \u0432\u0445\u043e\u0434\u0430. "
                    f"\u041f\u043e\u0432\u0442\u043e\u0440\u0438\u0442\u0435 \u0447\u0435\u0440\u0435\u0437 "
                    f"{rate_limit.retry_after_seconds} \u0441\u0435\u043a."
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
            {
                "title": "\u0412\u0445\u043e\u0434",
                "error": "\u041d\u0435\u0432\u0435\u0440\u043d\u044b\u0439 \u043b\u043e\u0433\u0438\u043d "
                "\u0438\u043b\u0438 \u043f\u0430\u0440\u043e\u043b\u044c",
            },
            status_code=400,
        )

    if user.is_blocked:
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "title": "\u0412\u0445\u043e\u0434",
                "error": "\u041f\u043e\u043b\u044c\u0437\u043e\u0432\u0430\u0442\u0435\u043b\u044c "
                "\u0437\u0430\u0431\u043b\u043e\u043a\u0438\u0440\u043e\u0432\u0430\u043d",
            },
            status_code=403,
        )
    access_until = normalize_datetime(user.access_until)
    if access_until and access_until < _now():
        return templates.TemplateResponse(
            request,
            "login.html",
            {
                "title": "\u0412\u0445\u043e\u0434",
                "error": "\u0421\u0440\u043e\u043a \u0434\u043e\u0441\u0442\u0443\u043f\u0430 "
                "\u0438\u0441\u0442\u0451\u043a",
            },
            status_code=403,
        )

    request.session["user_id"] = user.id
    rotate_csrf_token(request)
    redirect_to = "/admin" if user.role == UserRole.ADMIN else "/dashboard"
    return RedirectResponse(redirect_to, status_code=303)


@router.post("/logout")
def logout(
    request: Request,
    _: None = Depends(require_csrf_token),
) -> object:
    request.session.clear()
    return RedirectResponse("/login", status_code=303)
