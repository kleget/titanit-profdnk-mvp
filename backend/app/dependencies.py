from __future__ import annotations

from datetime import datetime, timezone

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.models import User, UserRole, normalize_datetime
from app.services.csrf import validate_csrf_request


def now_utc() -> datetime:
    return datetime.now(timezone.utc)


def get_optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    user_id = request.session.get("user_id")
    if not user_id:
        return None
    user = db.get(User, user_id)
    if not user:
        request.session.clear()
        return None
    return user


def require_user(user: User | None = Depends(get_optional_user)) -> User:
    if not user:
        raise HTTPException(
            status_code=status.HTTP_303_SEE_OTHER,
            headers={"Location": "/login"},
            detail="Auth required",
        )
    if user.is_blocked:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is blocked")
    normalized_access_until = normalize_datetime(user.access_until)
    if normalized_access_until and normalized_access_until < now_utc():
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Access expired")
    return user


def require_psychologist_or_admin(user: User = Depends(require_user)) -> User:
    if user.role not in {UserRole.ADMIN, UserRole.PSYCHOLOGIST}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Forbidden")
    return user


def require_admin(user: User = Depends(require_user)) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin only")
    return user


async def require_csrf_token(request: Request) -> None:
    csrf_error = await validate_csrf_request(request)
    if csrf_error:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=csrf_error)
