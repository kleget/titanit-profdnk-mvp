from __future__ import annotations

import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator, model_validator

from app.models import QuestionType
from app.services.client_fields import (
    ALLOWED_CUSTOM_FIELD_TYPES,
    ALLOWED_REPORT_BLOCKS,
    BUILTIN_CLIENT_FIELDS,
    RESERVED_CUSTOM_KEYS,
)
from app.services.logic import ALLOWED_LOGIC_OPERATORS, validate_condition_dependencies

CHOICE_QUESTION_TYPES = {QuestionType.SINGLE_CHOICE.value, QuestionType.MULTIPLE_CHOICE.value}
RANGE_QUESTION_TYPES = {
    QuestionType.NUMBER.value,
    QuestionType.SLIDER.value,
    QuestionType.RATING.value,
}
ALLOWED_QUESTION_TYPES = {item.value for item in QuestionType}


def _normalize_key(source: str, fallback: str) -> str:
    prepared = re.sub(r"[^a-zA-Z0-9_]+", "_", source.strip().lower())
    prepared = re.sub(r"_+", "_", prepared).strip("_")
    return (prepared or fallback)[:64]


def format_constructor_validation_error(exc: ValidationError) -> str:
    first_error = exc.errors()[0]
    raw_loc = ".".join(str(part) for part in first_error.get("loc", []))
    location = raw_loc.replace("sections_payload", "sections").replace(
        "formulas_payload", "formulas"
    )
    message = first_error.get("msg", "Некорректные данные")
    if location:
        return f"{location}: {message}"
    return str(message)


class ConstructorQuestionOptionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    label: str = Field(min_length=1, max_length=160)
    value: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z0-9_]+$")
    score: float = Field(default=1.0, ge=-100000, le=100000)


class ConstructorLogicConditionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    question_key: str = Field(min_length=1, max_length=128, pattern=r"^[a-zA-Z_][a-zA-Z0-9_]*$")
    operator: str
    value: str = Field(default="", max_length=255)

    @field_validator("operator")
    @classmethod
    def validate_operator(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_LOGIC_OPERATORS:
            raise ValueError(f"Неподдерживаемый оператор условия: {value}")
        return normalized

    @model_validator(mode="after")
    def validate_value_rules(self) -> "ConstructorLogicConditionSchema":
        if self.operator in {"is_true", "is_false", "empty", "not_empty"}:
            return self
        if not self.value.strip():
            raise ValueError("Для выбранного оператора нужно значение")
        return self


class ConstructorQuestionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str | None = Field(default=None, max_length=128)
    text: str = Field(min_length=1, max_length=2000)
    question_type: str
    required: bool = False
    options_json: list[ConstructorQuestionOptionSchema] | None = None
    min_value: float | None = None
    max_value: float | None = None
    weight: float = Field(default=1.0, gt=0, le=100)
    visibility_condition: ConstructorLogicConditionSchema | None = None

    @field_validator("question_type")
    @classmethod
    def validate_question_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_QUESTION_TYPES:
            raise ValueError(f"Неподдерживаемый тип вопроса: {value}")
        return normalized

    @model_validator(mode="after")
    def validate_by_type(self) -> "ConstructorQuestionSchema":
        if self.question_type in CHOICE_QUESTION_TYPES:
            options = self.options_json or []
            if len(options) < 2:
                raise ValueError(
                    f"Для типа '{self.question_type}' требуется минимум 2 варианта ответа"
                )
            seen_values: set[str] = set()
            for option in options:
                if option.value in seen_values:
                    raise ValueError("Значения options_json.value должны быть уникальными")
                seen_values.add(option.value)

        if (
            self.question_type in RANGE_QUESTION_TYPES
            and self.min_value is not None
            and self.max_value is not None
            and self.min_value > self.max_value
        ):
            raise ValueError("min_value не может быть больше max_value")

        return self


class ConstructorSectionSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=255)
    questions: list[ConstructorQuestionSchema] = Field(min_length=1, max_length=200)
    visibility_condition: ConstructorLogicConditionSchema | None = None


class ConstructorCustomFieldSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str | None = Field(default=None, max_length=64)
    label: str = Field(min_length=1, max_length=120)
    type: str = Field(default="text")
    required: bool = False
    placeholder: str = Field(default="", max_length=200)

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in ALLOWED_CUSTOM_FIELD_TYPES:
            raise ValueError(f"Неподдерживаемый тип пользовательского поля: {value}")
        return normalized


class ConstructorFormulaSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str | None = Field(default=None, max_length=128)
    label: str | None = Field(default=None, max_length=255)
    expression: str = Field(min_length=1, max_length=300)
    description: str = Field(default="", max_length=2000)


class ConstructorReportTemplatesSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    client: list[str] = Field(min_length=1, max_length=10)
    psychologist: list[str] = Field(min_length=1, max_length=10)

    @field_validator("client", "psychologist")
    @classmethod
    def validate_blocks(cls, blocks: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in blocks:
            key = raw.strip()
            if key not in ALLOWED_REPORT_BLOCKS:
                raise ValueError(f"Неподдерживаемый блок отчета: {raw}")
            if key in normalized:
                raise ValueError(f"Дублирующийся блок отчета: {raw}")
            normalized.append(key)
        if not normalized:
            raise ValueError("Список блоков отчета не может быть пустым")
        return normalized


class ConstructorPayloadSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    title: str = Field(min_length=5, max_length=255)
    description: str = Field(default="", max_length=4000)
    allow_client_report: bool = True
    required_client_fields: list[str] = Field(default_factory=lambda: ["full_name"])
    custom_client_fields: list[ConstructorCustomFieldSchema] = Field(
        default_factory=list, max_length=20
    )
    report_templates: ConstructorReportTemplatesSchema
    sections_payload: list[ConstructorSectionSchema] = Field(min_length=1, max_length=50)
    formulas_payload: list[ConstructorFormulaSchema] = Field(default_factory=list, max_length=50)

    @field_validator("required_client_fields")
    @classmethod
    def validate_required_client_fields(cls, fields: list[str]) -> list[str]:
        normalized: list[str] = []
        for raw in fields:
            field = raw.strip().lower()
            if field not in BUILTIN_CLIENT_FIELDS:
                raise ValueError(f"Неподдерживаемое встроенное поле клиента: {raw}")
            if field not in normalized:
                normalized.append(field)
        return ["full_name", *[field for field in normalized if field != "full_name"]]

    @model_validator(mode="after")
    def validate_payload_consistency(self) -> "ConstructorPayloadSchema":
        total_questions = sum(len(section.questions) for section in self.sections_payload)
        if total_questions <= 0:
            raise ValueError("Тест должен содержать минимум один вопрос")
        if total_questions > 500:
            raise ValueError("Превышен лимит количества вопросов (500)")

        custom_field_keys: set[str] = set()
        for idx, field in enumerate(self.custom_client_fields, start=1):
            key = _normalize_key(field.key or field.label, f"client_field_{idx}")
            if key in RESERVED_CUSTOM_KEYS:
                raise ValueError(f"Ключ пользовательского поля зарезервирован: {key}")
            if key in custom_field_keys:
                raise ValueError(f"Дублирующийся ключ пользовательского поля: {key}")
            custom_field_keys.add(key)

        formula_keys: set[str] = set()
        for idx, formula in enumerate(self.formulas_payload, start=1):
            key = _normalize_key(formula.key or formula.label or "", f"metric_{idx}")
            if key in formula_keys:
                raise ValueError(f"Дублирующийся ключ формулы: {key}")
            formula_keys.add(key)

        question_keys_in_order: list[str] = []
        question_conditions: list[dict | None] = []
        section_conditions: list[dict | None] = []
        section_question_counts: list[int] = []
        for section_index, section in enumerate(self.sections_payload, start=1):
            section_condition = (
                section.visibility_condition.model_dump() if section.visibility_condition else None
            )
            section_conditions.append(section_condition)
            section_question_counts.append(len(section.questions))
            for question_index, question in enumerate(section.questions, start=1):
                key = _normalize_key(
                    question.key or question.text,
                    f"question_{section_index}_{question_index}",
                )
                question_keys_in_order.append(key)
                question_conditions.append(
                    question.visibility_condition.model_dump()
                    if question.visibility_condition
                    else None
                )

        try:
            validate_condition_dependencies(
                question_keys_in_order=question_keys_in_order,
                section_conditions=section_conditions,
                question_conditions=question_conditions,
                section_question_counts=section_question_counts,
            )
        except ValueError as exc:
            raise ValueError(str(exc)) from exc

        return self

    def to_service_payload(self) -> dict[str, Any]:
        custom_fields_payload = []
        for idx, field in enumerate(self.custom_client_fields, start=1):
            custom_fields_payload.append(
                {
                    "key": _normalize_key(field.key or field.label, f"client_field_{idx}"),
                    "label": field.label,
                    "type": field.type,
                    "required": field.required,
                    "placeholder": field.placeholder,
                }
            )

        sections_payload = []
        for section_index, section in enumerate(self.sections_payload, start=1):
            questions = []
            for question_index, question in enumerate(section.questions, start=1):
                questions.append(
                    {
                        "key": _normalize_key(
                            question.key or question.text,
                            f"question_{section_index}_{question_index}",
                        ),
                        "text": question.text,
                        "question_type": question.question_type,
                        "required": question.required,
                        "options_json": (
                            [option.model_dump() for option in (question.options_json or [])]
                            or None
                        ),
                        "min_value": question.min_value,
                        "max_value": question.max_value,
                        "weight": question.weight,
                        "visibility_condition_json": (
                            question.visibility_condition.model_dump()
                            if question.visibility_condition
                            else None
                        ),
                    }
                )
            sections_payload.append(
                {
                    "title": section.title,
                    "questions": questions,
                    "visibility_condition_json": (
                        section.visibility_condition.model_dump()
                        if section.visibility_condition
                        else None
                    ),
                }
            )

        formulas_payload = []
        for idx, formula in enumerate(self.formulas_payload, start=1):
            resolved_key = _normalize_key(formula.key or formula.label or "", f"metric_{idx}")
            formulas_payload.append(
                {
                    "key": resolved_key,
                    "label": (formula.label or resolved_key).strip(),
                    "expression": formula.expression,
                    "description": formula.description,
                }
            )

        return {
            "title": self.title,
            "description": self.description,
            "allow_client_report": self.allow_client_report,
            "required_client_fields": self.required_client_fields,
            "custom_client_fields": custom_fields_payload,
            "report_templates": self.report_templates.model_dump(),
            "sections_payload": sections_payload,
            "formulas_payload": formulas_payload,
        }
