"""add admin audit logs

Revision ID: 20260321_0003
Revises: 20260321_0002
Create Date: 2026-03-21 17:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260321_0003"
down_revision = "20260321_0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "admin_audit_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("admin_user_id", sa.Integer(), nullable=False),
        sa.Column("target_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("target_email", sa.String(length=255), nullable=True),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["admin_user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_admin_audit_logs_admin_user_id",
        "admin_audit_logs",
        ["admin_user_id"],
        unique=False,
    )
    op.create_index(
        "ix_admin_audit_logs_target_user_id",
        "admin_audit_logs",
        ["target_user_id"],
        unique=False,
    )
    op.create_index("ix_admin_audit_logs_action", "admin_audit_logs", ["action"], unique=False)
    op.create_index(
        "ix_admin_audit_logs_created_at",
        "admin_audit_logs",
        ["created_at"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_admin_audit_logs_created_at", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_action", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_target_user_id", table_name="admin_audit_logs")
    op.drop_index("ix_admin_audit_logs_admin_user_id", table_name="admin_audit_logs")
    op.drop_table("admin_audit_logs")
