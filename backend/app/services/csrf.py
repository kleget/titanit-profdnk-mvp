from __future__ import annotations

import secrets
from hmac import compare_digest

from fastapi import Request


CSRF_SESSION_KEY = "csrf_token"
CSRF_FORM_FIELD = "csrf_token"
CSRF_HEADER_NAME = "x-csrf-token"


def ensure_csrf_token(request: Request) -> str:
    raw_token = request.session.get(CSRF_SESSION_KEY)
    if isinstance(raw_token, str) and raw_token.strip():
        return raw_token
    token = secrets.token_urlsafe(32)
    request.session[CSRF_SESSION_KEY] = token
    return token


def rotate_csrf_token(request: Request) -> str:
    token = secrets.token_urlsafe(32)
    request.session[CSRF_SESSION_KEY] = token
    return token


def _token_from_headers(request: Request) -> str | None:
    value = request.headers.get(CSRF_HEADER_NAME, "").strip()
    return value or None


async def _token_from_form(request: Request) -> str | None:
    content_type = request.headers.get("content-type", "").lower()
    if (
        "application/x-www-form-urlencoded" not in content_type
        and "multipart/form-data" not in content_type
    ):
        return None
    form = await request.form()
    raw_value = form.get(CSRF_FORM_FIELD)
    if isinstance(raw_value, str):
        cleaned = raw_value.strip()
        return cleaned or None
    return None


async def validate_csrf_request(request: Request) -> str | None:
    expected_token = request.session.get(CSRF_SESSION_KEY)
    if not isinstance(expected_token, str) or not expected_token.strip():
        return "CSRF-токен не найден. Обновите страницу и повторите действие."

    provided_token = _token_from_headers(request)
    if provided_token is None:
        provided_token = await _token_from_form(request)

    if not provided_token or not compare_digest(provided_token, expected_token):
        return "Некорректный CSRF-токен. Обновите страницу и повторите действие."
    return None
