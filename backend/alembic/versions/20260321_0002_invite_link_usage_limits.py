"""add invite link usage limits

Revision ID: 20260321_0002
Revises: 20260321_0001
Create Date: 2026-03-21 12:10:00.000000
"""

from __future__ import annotations

import json

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260321_0002"
down_revision = "20260321_0001"
branch_labels = None
depends_on = None


def _extract_invite_link_id(raw_extra: object) -> int | None:
    if raw_extra is None:
        return None

    extra_data: object = raw_extra
    if isinstance(raw_extra, str):
        try:
            extra_data = json.loads(raw_extra)
        except json.JSONDecodeError:
            return None

    if not isinstance(extra_data, dict):
        return None

    raw_link_id = extra_data.get("invite_link_id")
    if isinstance(raw_link_id, int):
        return raw_link_id
    if isinstance(raw_link_id, str) and raw_link_id.isdigit():
        return int(raw_link_id)
    return None


def upgrade() -> None:
    op.add_column("invite_links", sa.Column("usage_limit", sa.Integer(), nullable=True))
    op.add_column(
        "invite_links",
        sa.Column("usage_count", sa.Integer(), nullable=False, server_default=sa.text("0")),
    )

    connection = op.get_bind()
    submissions = connection.execute(sa.text("SELECT client_extra_json FROM submissions")).fetchall()

    usage_counts: dict[int, int] = {}
    for (raw_extra,) in submissions:
        link_id = _extract_invite_link_id(raw_extra)
        if link_id is None:
            continue
        usage_counts[link_id] = usage_counts.get(link_id, 0) + 1

    for link_id, count in usage_counts.items():
        connection.execute(
            sa.text("UPDATE invite_links SET usage_count = :count WHERE id = :id"),
            {"count": count, "id": link_id},
        )

    connection.execute(
        sa.text(
            "UPDATE invite_links "
            "SET is_active = 0 "
            "WHERE usage_limit IS NOT NULL AND usage_count >= usage_limit"
        )
    )

def downgrade() -> None:
    op.drop_column("invite_links", "usage_count")
    op.drop_column("invite_links", "usage_limit")
