from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import AdminAuditLog


def log_admin_action(
    db: Session,
    *,
    admin_user_id: int,
    action: str,
    target_user_id: int | None = None,
    target_email: str | None = None,
    details: dict | None = None,
) -> None:
    log_entry = AdminAuditLog(
        admin_user_id=admin_user_id,
        target_user_id=target_user_id,
        action=action,
        target_email=target_email,
        details_json=details or None,
    )
    db.add(log_entry)


def recent_admin_audit_logs(
    db: Session,
    *,
    limit: int = 30,
) -> list[AdminAuditLog]:
    safe_limit = max(1, min(limit, 200))
    return db.scalars(
        select(AdminAuditLog).order_by(AdminAuditLog.created_at.desc()).limit(safe_limit)
    ).all()
