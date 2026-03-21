from __future__ import annotations

import re

from passlib.context import CryptContext

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

_PASSWORD_LOWER_RE = re.compile(r"[a-zа-яё]")
_PASSWORD_UPPER_RE = re.compile(r"[A-ZА-ЯЁ]")
_PASSWORD_DIGIT_RE = re.compile(r"\d")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def validate_password_policy(password: str) -> str | None:
    if len(password) < 8:
        return "Пароль должен быть не короче 8 символов."
    if not _PASSWORD_LOWER_RE.search(password):
        return "Пароль должен содержать хотя бы одну строчную букву."
    if not _PASSWORD_UPPER_RE.search(password):
        return "Пароль должен содержать хотя бы одну заглавную букву."
    if not _PASSWORD_DIGIT_RE.search(password):
        return "Пароль должен содержать хотя бы одну цифру."
    return None
