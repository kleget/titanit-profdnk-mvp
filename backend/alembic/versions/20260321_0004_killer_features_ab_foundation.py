"""killer features A/B foundation schema

Revision ID: 20260321_0004
Revises: 20260321_0003
Create Date: 2026-03-21 19:00:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260321_0004"
down_revision = "20260321_0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("test_sections", sa.Column("visibility_condition_json", sa.JSON(), nullable=True))
    op.add_column("questions", sa.Column("visibility_condition_json", sa.JSON(), nullable=True))

    op.add_column("invite_links", sa.Column("start_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("invite_links", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "invite_links",
        sa.Column(
            "single_use",
            sa.Boolean(),
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column("invite_links", sa.Column("target_client_name", sa.String(length=255), nullable=True))

    op.create_table(
        "test_change_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("action", sa.String(length=100), nullable=False),
        sa.Column("details_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_change_logs_test_id", "test_change_logs", ["test_id"], unique=False)
    op.create_index(
        "ix_test_change_logs_actor_user_id",
        "test_change_logs",
        ["actor_user_id"],
        unique=False,
    )
    op.create_index("ix_test_change_logs_action", "test_change_logs", ["action"], unique=False)
    op.create_index(
        "ix_test_change_logs_created_at",
        "test_change_logs",
        ["created_at"],
        unique=False,
    )

    op.alter_column("invite_links", "single_use", server_default=None)


def downgrade() -> None:
    op.drop_index("ix_test_change_logs_created_at", table_name="test_change_logs")
    op.drop_index("ix_test_change_logs_action", table_name="test_change_logs")
    op.drop_index("ix_test_change_logs_actor_user_id", table_name="test_change_logs")
    op.drop_index("ix_test_change_logs_test_id", table_name="test_change_logs")
    op.drop_table("test_change_logs")

    op.drop_column("invite_links", "target_client_name")
    op.drop_column("invite_links", "single_use")
    op.drop_column("invite_links", "expires_at")
    op.drop_column("invite_links", "start_at")

    op.drop_column("questions", "visibility_condition_json")
    op.drop_column("test_sections", "visibility_condition_json")
