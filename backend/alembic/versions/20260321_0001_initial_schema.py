"""initial schema

Revision ID: 20260321_0001
Revises:
Create Date: 2026-03-21 07:20:00.000000
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = "20260321_0001"
down_revision = None
branch_labels = None
depends_on = None


user_role_enum = sa.Enum("ADMIN", "PSYCHOLOGIST", name="userrole")
question_type_enum = sa.Enum(
    "TEXT",
    "TEXTAREA",
    "SINGLE_CHOICE",
    "MULTIPLE_CHOICE",
    "YES_NO",
    "NUMBER",
    "SLIDER",
    "DATETIME",
    "RATING",
    name="questiontype",
)


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("phone", sa.String(length=64), nullable=True),
        sa.Column("role", user_role_enum, nullable=False),
        sa.Column("access_until", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_blocked", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("about_md", sa.Text(), nullable=False, server_default=""),
        sa.Column("photo_filename", sa.String(length=512), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "tests",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("psychologist_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("share_token", sa.String(length=120), nullable=False),
        sa.Column("required_client_fields", sa.JSON(), nullable=False),
        sa.Column(
            "allow_client_report", sa.Boolean(), nullable=False, server_default=sa.text("1")
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["psychologist_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("share_token"),
    )
    op.create_index("ix_tests_psychologist_id", "tests", ["psychologist_id"], unique=False)
    op.create_index("ix_tests_share_token", "tests", ["share_token"], unique=True)

    op.create_table(
        "test_sections",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_test_sections_test_id", "test_sections", ["test_id"], unique=False)

    op.create_table(
        "questions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("section_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("question_type", question_type_enum, nullable=False),
        sa.Column("required", sa.Boolean(), nullable=False, server_default=sa.text("0")),
        sa.Column("options_json", sa.JSON(), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("weight", sa.Float(), nullable=False, server_default="1"),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.ForeignKeyConstraint(["section_id"], ["test_sections.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("section_id", "key", name="uq_question_key_per_section"),
    )
    op.create_index("ix_questions_section_id", "questions", ["section_id"], unique=False)

    op.create_table(
        "submissions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("client_full_name", sa.String(length=255), nullable=False),
        sa.Column("client_email", sa.String(length=255), nullable=True),
        sa.Column("client_phone", sa.String(length=64), nullable=True),
        sa.Column("client_extra_json", sa.JSON(), nullable=True),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("metrics_json", sa.JSON(), nullable=True),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_submissions_client_full_name", "submissions", ["client_full_name"], unique=False)
    op.create_index("ix_submissions_submitted_at", "submissions", ["submitted_at"], unique=False)
    op.create_index("ix_submissions_test_id", "submissions", ["test_id"], unique=False)

    op.create_table(
        "answers",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("submission_id", sa.Integer(), nullable=False),
        sa.Column("question_id", sa.Integer(), nullable=False),
        sa.Column("value_json", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["question_id"], ["questions.id"]),
        sa.ForeignKeyConstraint(["submission_id"], ["submissions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_answers_question_id", "answers", ["question_id"], unique=False)
    op.create_index("ix_answers_submission_id", "answers", ["submission_id"], unique=False)

    op.create_table(
        "metric_formulas",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("key", sa.String(length=128), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("expression", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=False, server_default=""),
        sa.Column("position", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("test_id", "key", name="uq_metric_formula_key_per_test"),
    )
    op.create_index("ix_metric_formulas_test_id", "metric_formulas", ["test_id"], unique=False)

    op.create_table(
        "invite_links",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_id", sa.Integer(), nullable=False),
        sa.Column("label", sa.String(length=255), nullable=False),
        sa.Column("token", sa.String(length=120), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["test_id"], ["tests.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("token"),
        sa.UniqueConstraint("test_id", "label", name="uq_invite_link_label_per_test"),
    )
    op.create_index("ix_invite_links_test_id", "invite_links", ["test_id"], unique=False)
    op.create_index("ix_invite_links_token", "invite_links", ["token"], unique=True)


def downgrade() -> None:
    op.drop_index("ix_invite_links_token", table_name="invite_links")
    op.drop_index("ix_invite_links_test_id", table_name="invite_links")
    op.drop_table("invite_links")

    op.drop_index("ix_metric_formulas_test_id", table_name="metric_formulas")
    op.drop_table("metric_formulas")

    op.drop_index("ix_answers_submission_id", table_name="answers")
    op.drop_index("ix_answers_question_id", table_name="answers")
    op.drop_table("answers")

    op.drop_index("ix_submissions_test_id", table_name="submissions")
    op.drop_index("ix_submissions_submitted_at", table_name="submissions")
    op.drop_index("ix_submissions_client_full_name", table_name="submissions")
    op.drop_table("submissions")

    op.drop_index("ix_questions_section_id", table_name="questions")
    op.drop_table("questions")

    op.drop_index("ix_test_sections_test_id", table_name="test_sections")
    op.drop_table("test_sections")

    op.drop_index("ix_tests_share_token", table_name="tests")
    op.drop_index("ix_tests_psychologist_id", table_name="tests")
    op.drop_table("tests")

    op.drop_index("ix_users_email", table_name="users")
    op.drop_table("users")

    bind = op.get_bind()
    question_type_enum.drop(bind, checkfirst=True)
    user_role_enum.drop(bind, checkfirst=True)
