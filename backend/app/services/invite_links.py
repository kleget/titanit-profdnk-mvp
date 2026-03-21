from __future__ import annotations

from app.models import InviteLink

INVITE_LINK_STATE_ACTIVE = "active"
INVITE_LINK_STATE_EXHAUSTED = "exhausted"
INVITE_LINK_STATE_DISABLED = "disabled"
INVITE_LINK_STATE_UNKNOWN = "unknown"


def is_invite_link_exhausted(link: InviteLink) -> bool:
    if link.usage_limit is None:
        return False
    return link.usage_count >= link.usage_limit


def invite_link_state(link: InviteLink) -> str:
    if is_invite_link_exhausted(link):
        return INVITE_LINK_STATE_EXHAUSTED
    if link.is_active:
        return INVITE_LINK_STATE_ACTIVE
    return INVITE_LINK_STATE_DISABLED


def invite_link_state_label(state: str) -> str:
    labels = {
        INVITE_LINK_STATE_ACTIVE: "Активна",
        INVITE_LINK_STATE_EXHAUSTED: "Лимит исчерпан",
        INVITE_LINK_STATE_DISABLED: "Отключена",
        INVITE_LINK_STATE_UNKNOWN: "Неизвестно",
    }
    return labels.get(state, labels[INVITE_LINK_STATE_UNKNOWN])


def invite_link_limit_text(link: InviteLink) -> str:
    if link.usage_limit is None:
        return f"{link.usage_count} / без лимита"
    return f"{link.usage_count} / {link.usage_limit}"
