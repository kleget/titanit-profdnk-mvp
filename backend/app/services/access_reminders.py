from __future__ import annotations

from datetime import datetime, timezone

from app.models import User, normalize_datetime

REMINDER_DAYS = {7, 3, 1}


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _plural_days(days: int) -> str:
    if days % 10 == 1 and days % 100 != 11:
        return "день"
    if days % 10 in {2, 3, 4} and days % 100 not in {12, 13, 14}:
        return "дня"
    return "дней"


def days_until_access_end(access_until: datetime | None, now: datetime | None = None) -> int | None:
    normalized_access = normalize_datetime(access_until)
    if not normalized_access:
        return None
    current = normalize_datetime(now) or _now_utc()
    return (normalized_access.date() - current.date()).days


def build_psychologist_access_reminder(
    user: User, now: datetime | None = None
) -> dict[str, object] | None:
    days_left = days_until_access_end(user.access_until, now=now)
    if days_left is None or days_left not in REMINDER_DAYS:
        return None
    normalized_access = normalize_datetime(user.access_until)
    if not normalized_access:
        return None
    return {
        "days_left": days_left,
        "level": "warning" if days_left == 1 else "info",
        "message": (
            f"Ваш доступ истекает через {days_left} {_plural_days(days_left)} "
            f"({normalized_access.strftime('%Y-%m-%d')}). "
            "Обратитесь к администратору для продления."
        ),
    }


def build_admin_access_expiry_reminders(
    psychologists: list[User], now: datetime | None = None
) -> list[dict[str, object]]:
    reminders: list[dict[str, object]] = []
    for psychologist in psychologists:
        days_left = days_until_access_end(psychologist.access_until, now=now)
        if days_left is None or days_left not in REMINDER_DAYS:
            continue
        normalized_access = normalize_datetime(psychologist.access_until)
        if not normalized_access:
            continue
        reminders.append(
            {
                "id": psychologist.id,
                "full_name": psychologist.full_name,
                "email": psychologist.email,
                "days_left": days_left,
                "access_until": normalized_access,
                "level": "warning" if days_left == 1 else "info",
                "message": (
                    f"Доступ истекает через {days_left} {_plural_days(days_left)} "
                    f"({normalized_access.strftime('%Y-%m-%d')})."
                ),
            }
        )

    return sorted(reminders, key=lambda item: (int(item["days_left"]), str(item["full_name"])))
