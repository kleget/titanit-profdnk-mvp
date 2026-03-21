from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    JSON,
    Boolean,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


def utcnow() -> datetime:
    return datetime.now(timezone.utc)


def normalize_datetime(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


class UserRole(str, enum.Enum):
    ADMIN = "admin"
    PSYCHOLOGIST = "psychologist"


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(64))
    role: Mapped[UserRole] = mapped_column(default=UserRole.PSYCHOLOGIST, nullable=False)
    access_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    about_md: Mapped[str] = mapped_column(Text, default="", nullable=False)
    photo_filename: Mapped[str | None] = mapped_column(String(512))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    tests: Mapped[list[Test]] = relationship(
        back_populates="psychologist", cascade="all, delete-orphan"
    )
    admin_audit_logs: Mapped[list[AdminAuditLog]] = relationship(
        back_populates="admin_user",
        foreign_keys="AdminAuditLog.admin_user_id",
    )

    def has_access(self) -> bool:
        if self.is_blocked:
            return False
        access_until = normalize_datetime(self.access_until)
        if access_until is None:
            return True
        return access_until >= utcnow()


class Test(Base):
    __tablename__ = "tests"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    psychologist_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    share_token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    required_client_fields: Mapped[dict | list[str]] = mapped_column(
        JSON, default=lambda: ["full_name"], nullable=False
    )
    allow_client_report: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, onupdate=utcnow, nullable=False
    )

    psychologist: Mapped[User] = relationship(back_populates="tests")
    sections: Mapped[list[TestSection]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="TestSection.position",
    )
    submissions: Mapped[list[Submission]] = relationship(
        back_populates="test", cascade="all, delete-orphan"
    )
    invite_links: Mapped[list[InviteLink]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="InviteLink.created_at.desc()",
    )
    formulas: Mapped[list[MetricFormula]] = relationship(
        back_populates="test",
        cascade="all, delete-orphan",
        order_by="MetricFormula.position",
    )


class TestSection(Base):
    __tablename__ = "test_sections"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    test: Mapped[Test] = relationship(back_populates="sections")
    questions: Mapped[list[Question]] = relationship(
        back_populates="section",
        cascade="all, delete-orphan",
        order_by="Question.position",
    )


class QuestionType(str, enum.Enum):
    TEXT = "text"
    TEXTAREA = "textarea"
    SINGLE_CHOICE = "single_choice"
    MULTIPLE_CHOICE = "multiple_choice"
    YES_NO = "yes_no"
    NUMBER = "number"
    SLIDER = "slider"
    DATETIME = "datetime"
    RATING = "rating"


class Question(Base):
    __tablename__ = "questions"
    __table_args__ = (UniqueConstraint("section_id", "key", name="uq_question_key_per_section"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    section_id: Mapped[int] = mapped_column(
        ForeignKey("test_sections.id"), nullable=False, index=True
    )
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    question_type: Mapped[QuestionType] = mapped_column(nullable=False)
    required: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    options_json: Mapped[list[dict] | None] = mapped_column(JSON)
    min_value: Mapped[float | None] = mapped_column(Float)
    max_value: Mapped[float | None] = mapped_column(Float)
    weight: Mapped[float] = mapped_column(Float, default=1.0, nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    section: Mapped[TestSection] = relationship(back_populates="questions")
    answers: Mapped[list[Answer]] = relationship(
        back_populates="question", cascade="all, delete-orphan"
    )


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    client_full_name: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    client_email: Mapped[str | None] = mapped_column(String(255))
    client_phone: Mapped[str | None] = mapped_column(String(64))
    client_extra_json: Mapped[dict | None] = mapped_column(JSON)
    score: Mapped[float | None] = mapped_column(Float)
    metrics_json: Mapped[dict | None] = mapped_column(JSON)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    test: Mapped[Test] = relationship(back_populates="submissions")
    answers: Mapped[list[Answer]] = relationship(
        back_populates="submission", cascade="all, delete-orphan"
    )


class Answer(Base):
    __tablename__ = "answers"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    submission_id: Mapped[int] = mapped_column(
        ForeignKey("submissions.id"), nullable=False, index=True
    )
    question_id: Mapped[int] = mapped_column(ForeignKey("questions.id"), nullable=False, index=True)
    value_json: Mapped[object] = mapped_column(JSON, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    submission: Mapped[Submission] = relationship(back_populates="answers")
    question: Mapped[Question] = relationship(back_populates="answers")


class MetricFormula(Base):
    __tablename__ = "metric_formulas"
    __table_args__ = (UniqueConstraint("test_id", "key", name="uq_metric_formula_key_per_test"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    key: Mapped[str] = mapped_column(String(128), nullable=False)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    expression: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str] = mapped_column(Text, default="", nullable=False)
    position: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    test: Mapped[Test] = relationship(back_populates="formulas")


class InviteLink(Base):
    __tablename__ = "invite_links"
    __table_args__ = (UniqueConstraint("test_id", "label", name="uq_invite_link_label_per_test"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    test_id: Mapped[int] = mapped_column(ForeignKey("tests.id"), nullable=False, index=True)
    label: Mapped[str] = mapped_column(String(255), nullable=False)
    token: Mapped[str] = mapped_column(String(120), unique=True, nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    usage_limit: Mapped[int | None] = mapped_column(Integer)
    usage_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False
    )

    test: Mapped[Test] = relationship(back_populates="invite_links")


class AdminAuditLog(Base):
    __tablename__ = "admin_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    admin_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    target_user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id"), index=True)
    action: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    target_email: Mapped[str | None] = mapped_column(String(255))
    details_json: Mapped[dict | None] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utcnow, nullable=False, index=True
    )

    admin_user: Mapped[User] = relationship(
        back_populates="admin_audit_logs",
        foreign_keys=[admin_user_id],
    )
