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


def _table_exists(table_name: str) -> bool:
    inspector = sa.inspect(op.get_bind())
    return inspector.has_table(table_name)


def _column_exists(table_name: str, column_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(column["name"] == column_name for column in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    if not _table_exists(table_name):
        return False
    inspector = sa.inspect(op.get_bind())
    return any(index["name"] == index_name for index in inspector.get_indexes(table_name))


def upgrade() -> None:
    if not _column_exists("test_sections", "visibility_condition_json"):
        op.add_column("test_sections", sa.Column("visibility_condition_json", sa.JSON(), nullable=True))
    if not _column_exists("questions", "visibility_condition_json"):
        op.add_column("questions", sa.Column("visibility_condition_json", sa.JSON(), nullable=True))

    if not _column_exists("invite_links", "start_at"):
        op.add_column("invite_links", sa.Column("start_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("invite_links", "expires_at"):
        op.add_column("invite_links", sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True))
    if not _column_exists("invite_links", "single_use"):
        op.add_column(
            "invite_links",
            sa.Column(
                "single_use",
                sa.Boolean(),
                nullable=False,
                server_default=sa.false(),
            ),
        )
    if not _column_exists("invite_links", "target_client_name"):
        op.add_column("invite_links", sa.Column("target_client_name", sa.String(length=255), nullable=True))

    if not _table_exists("test_change_logs"):
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

    if not _index_exists("test_change_logs", "ix_test_change_logs_test_id"):
        op.create_index("ix_test_change_logs_test_id", "test_change_logs", ["test_id"], unique=False)
    if not _index_exists("test_change_logs", "ix_test_change_logs_actor_user_id"):
        op.create_index(
            "ix_test_change_logs_actor_user_id",
            "test_change_logs",
            ["actor_user_id"],
            unique=False,
        )
    if not _index_exists("test_change_logs", "ix_test_change_logs_action"):
        op.create_index("ix_test_change_logs_action", "test_change_logs", ["action"], unique=False)
    if not _index_exists("test_change_logs", "ix_test_change_logs_created_at"):
        op.create_index(
            "ix_test_change_logs_created_at",
            "test_change_logs",
            ["created_at"],
            unique=False,
        )

    bind = op.get_bind()
    if bind.dialect.name != "sqlite" and _column_exists("invite_links", "single_use"):
        op.alter_column("invite_links", "single_use", server_default=None)


def downgrade() -> None:
    if _index_exists("test_change_logs", "ix_test_change_logs_created_at"):
        op.drop_index("ix_test_change_logs_created_at", table_name="test_change_logs")
    if _index_exists("test_change_logs", "ix_test_change_logs_action"):
        op.drop_index("ix_test_change_logs_action", table_name="test_change_logs")
    if _index_exists("test_change_logs", "ix_test_change_logs_actor_user_id"):
        op.drop_index("ix_test_change_logs_actor_user_id", table_name="test_change_logs")
    if _index_exists("test_change_logs", "ix_test_change_logs_test_id"):
        op.drop_index("ix_test_change_logs_test_id", table_name="test_change_logs")
    if _table_exists("test_change_logs"):
        op.drop_table("test_change_logs")

    if _column_exists("invite_links", "target_client_name"):
        op.drop_column("invite_links", "target_client_name")
    if _column_exists("invite_links", "single_use"):
        op.drop_column("invite_links", "single_use")
    if _column_exists("invite_links", "expires_at"):
        op.drop_column("invite_links", "expires_at")
    if _column_exists("invite_links", "start_at"):
        op.drop_column("invite_links", "start_at")

    if _column_exists("questions", "visibility_condition_json"):
        op.drop_column("questions", "visibility_condition_json")
    if _column_exists("test_sections", "visibility_condition_json"):
        op.drop_column("test_sections", "visibility_condition_json")
