from __future__ import annotations

import math
import re
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


KEY_PATTERN = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _normalize_key(source: str, fallback: str) -> str:
    prepared = re.sub(r"[^a-zA-Z0-9_]+", "_", source.strip().lower())
    prepared = re.sub(r"_+", "_", prepared).strip("_")
    return (prepared or fallback)[:128]


class FormulaPreviewFormulaSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    key: str | None = Field(default=None, max_length=128)
    label: str | None = Field(default=None, max_length=255)
    expression: str = Field(min_length=1, max_length=300)


class FormulaPreviewPayloadSchema(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    formulas: list[FormulaPreviewFormulaSchema] = Field(min_length=1, max_length=50)
    context: dict[str, float] = Field(default_factory=dict)

    @field_validator("context")
    @classmethod
    def validate_context(cls, value: dict[str, float]) -> dict[str, float]:
        normalized: dict[str, float] = {}
        for raw_key, raw_number in value.items():
            key = raw_key.strip()
            if not key:
                continue
            if not KEY_PATTERN.fullmatch(key):
                raise ValueError(f"Некорректный ключ контекста: {raw_key}")
            number = float(raw_number)
            if not math.isfinite(number):
                raise ValueError(f"Некорректное число для ключа {raw_key}")
            normalized[key] = number
        return normalized

    @model_validator(mode="after")
    def validate_formula_keys(self) -> "FormulaPreviewPayloadSchema":
        seen: set[str] = set()
        for idx, formula in enumerate(self.formulas, start=1):
            key = _normalize_key(formula.key or formula.label or "", f"metric_{idx}")
            if key in seen:
                raise ValueError(f"Дублирующийся ключ формулы: {key}")
            seen.add(key)
        return self

    def to_service_payload(self) -> dict[str, Any]:
        formulas_payload: list[dict[str, str]] = []
        for idx, formula in enumerate(self.formulas, start=1):
            key = _normalize_key(formula.key or formula.label or "", f"metric_{idx}")
            label = (formula.label or key).strip()
            formulas_payload.append(
                {
                    "key": key,
                    "label": label,
                    "expression": formula.expression.strip(),
                }
            )
        return {
            "formulas": formulas_payload,
            "context": dict(self.context),
        }
