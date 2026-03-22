from __future__ import annotations

from datetime import datetime, timezone

from app.models import InviteLink

INVITE_LINK_STATE_ACTIVE = "active"
INVITE_LINK_STATE_EXHAUSTED = "exhausted"
INVITE_LINK_STATE_DISABLED = "disabled"
INVITE_LINK_STATE_PENDING = "pending"
INVITE_LINK_STATE_EXPIRED = "expired"
INVITE_LINK_STATE_UNKNOWN = "unknown"


def _now_utc() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_datetime(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def is_invite_link_exhausted(link: InviteLink) -> bool:
    if link.single_use and link.usage_count >= 1:
        return True
    if link.usage_limit is None:
        return False
    return link.usage_count >= link.usage_limit


def is_invite_link_pending(link: InviteLink, *, now: datetime | None = None) -> bool:
    started_at = _normalize_datetime(link.start_at)
    if started_at is None:
        return False
    current = _normalize_datetime(now) or _now_utc()
    return current < started_at


def is_invite_link_expired(link: InviteLink, *, now: datetime | None = None) -> bool:
    expires_at = _normalize_datetime(link.expires_at)
    if expires_at is None:
        return False
    current = _normalize_datetime(now) or _now_utc()
    return current > expires_at


def is_invite_link_available(link: InviteLink, *, now: datetime | None = None) -> bool:
    if not link.is_active:
        return False
    if is_invite_link_pending(link, now=now):
        return False
    if is_invite_link_expired(link, now=now):
        return False
    if is_invite_link_exhausted(link):
        return False
    return True


def invite_link_state(link: InviteLink) -> str:
    if is_invite_link_exhausted(link):
        return INVITE_LINK_STATE_EXHAUSTED
    if is_invite_link_expired(link):
        return INVITE_LINK_STATE_EXPIRED
    if not link.is_active:
        return INVITE_LINK_STATE_DISABLED
    if is_invite_link_pending(link):
        return INVITE_LINK_STATE_PENDING
    if link.is_active:
        return INVITE_LINK_STATE_ACTIVE
    return INVITE_LINK_STATE_UNKNOWN


def invite_link_state_label(state: str) -> str:
    labels = {
        INVITE_LINK_STATE_ACTIVE: "Активна",
        INVITE_LINK_STATE_PENDING: "Ожидает старта",
        INVITE_LINK_STATE_EXPIRED: "Истекла",
        INVITE_LINK_STATE_EXHAUSTED: "Лимит исчерпан",
        INVITE_LINK_STATE_DISABLED: "Отключена",
        INVITE_LINK_STATE_UNKNOWN: "Неизвестно",
    }
    return labels.get(state, labels[INVITE_LINK_STATE_UNKNOWN])


def invite_link_limit_text(link: InviteLink) -> str:
    if link.single_use:
        return f"{link.usage_count} / 1"
    if link.usage_limit is None:
        return f"{link.usage_count} / без лимита"
    return f"{link.usage_count} / {link.usage_limit}"
