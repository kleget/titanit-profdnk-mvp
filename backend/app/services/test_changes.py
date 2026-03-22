from __future__ import annotations

from sqlalchemy.orm import Session

from app.models import TestChangeLog


def log_test_change(
    db: Session,
    *,
    test_id: int,
    action: str,
    actor_user_id: int | None = None,
    details: dict | None = None,
) -> None:
    db.add(
        TestChangeLog(
            test_id=test_id,
            actor_user_id=actor_user_id,
            action=action,
            details_json=details or None,
        )
    )
