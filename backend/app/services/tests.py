from __future__ import annotations

import re
import secrets
from collections import OrderedDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import MetricFormula, Question, QuestionType, Test, TestSection
from app.services.client_fields import (
    ALLOWED_CUSTOM_FIELD_TYPES,
    RESERVED_CUSTOM_KEYS,
    normalize_client_fields_config,
    normalize_report_templates,
    pack_client_fields_config,
)


def normalize_key(source: str, fallback: str) -> str:
    prepared = re.sub(r"[^a-zA-Z0-9_]+", "_", source.strip().lower())
    prepared = re.sub(r"_+", "_", prepared).strip("_")
    return prepared or fallback


def parse_options(raw: str) -> list[dict] | None:
    if not raw or not raw.strip():
        return None
    options: list[dict] = []
    for chunk in raw.split(","):
        item = chunk.strip()
        if not item:
            continue
        if ":" in item:
            label, score_raw = item.rsplit(":", 1)
            label = label.strip()
            try:
                score = float(score_raw.strip())
            except ValueError:
                score = 1.0
            value = normalize_key(label, f"option_{len(options)+1}")
            options.append({"label": label, "value": value, "score": score})
        else:
            label = item
            value = normalize_key(label, f"option_{len(options)+1}")
            options.append({"label": label, "value": value, "score": 1.0})
    return options or None


def create_test_from_payload(
    db: Session,
    psychologist_id: int,
    title: str,
    description: str,
    allow_client_report: bool,
    required_client_fields: list[str],
    custom_client_fields: list[dict] | None,
    report_templates: dict[str, list[str]] | None,
    sections_payload: list[dict],
    formulas_payload: list[dict] | None = None,
) -> Test:
    if not title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required")
    if not sections_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one section required")

    required_fields = ["full_name"]
    required_fields.extend([field for field in required_client_fields if field != "full_name"])
    client_fields_config = pack_client_fields_config(
        required_builtin_fields=required_fields,
        custom_fields=custom_client_fields or [],
        report_templates=report_templates,
    )

    test = Test(
        psychologist_id=psychologist_id,
        title=title.strip(),
        description=description.strip(),
        allow_client_report=allow_client_report,
        required_client_fields=client_fields_config,
        share_token=secrets.token_urlsafe(12),
    )
    db.add(test)
    db.flush()

    for section_pos, section_payload in enumerate(sections_payload, start=1):
        section_title = (section_payload.get("title") or "").strip()
        if not section_title:
            continue
        section = TestSection(test_id=test.id, title=section_title, position=section_pos)
        db.add(section)
        db.flush()
        questions_payload = section_payload.get("questions") or []
        for question_pos, q in enumerate(questions_payload, start=1):
            q_type = q.get("question_type")
            if q_type not in {member.value for member in QuestionType}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Unsupported question type: {q_type}",
                )
            text = (q.get("text") or "").strip()
            if not text:
                continue
            key = normalize_key(q.get("key") or text, f"q_{question_pos}")
            question = Question(
                section_id=section.id,
                key=key,
                text=text,
                question_type=QuestionType(q_type),
                required=bool(q.get("required", False)),
                options_json=q.get("options_json"),
                min_value=q.get("min_value"),
                max_value=q.get("max_value"),
                weight=float(q.get("weight") or 1.0),
                position=question_pos,
            )
            db.add(question)

    used_formula_keys: set[str] = set()
    for formula_pos, formula in enumerate(formulas_payload or [], start=1):
        key = normalize_key(str(formula.get("key") or ""), f"metric_{formula_pos}")
        if key in used_formula_keys:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Duplicate formula key: {key}",
            )
        used_formula_keys.add(key)
        label = str(formula.get("label") or "").strip() or key
        expression = str(formula.get("expression") or "").strip()
        description = str(formula.get("description") or "").strip()
        if not expression:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Formula expression is required for {label}",
            )
        db.add(
            MetricFormula(
                test_id=test.id,
                key=key,
                label=label,
                expression=expression,
                description=description,
                position=formula_pos,
            )
        )

    db.commit()
    db.refresh(test)
    return test


def export_test_config(test: Test) -> dict:
    client_fields = normalize_client_fields_config(test.required_client_fields)
    sections: list[dict] = []
    for section in test.sections:
        questions: list[dict] = []
        for question in section.questions:
            questions.append(
                {
                    "key": question.key,
                    "text": question.text,
                    "question_type": question.question_type.value,
                    "required": question.required,
                    "options_json": question.options_json,
                    "min_value": question.min_value,
                    "max_value": question.max_value,
                    "weight": question.weight,
                    "position": question.position,
                }
            )
        sections.append({"title": section.title, "position": section.position, "questions": questions})

    return {
        "title": test.title,
        "description": test.description,
        "allow_client_report": test.allow_client_report,
        "required_client_fields": client_fields["required_builtin_fields"],
        "custom_client_fields": client_fields["custom_fields"],
        "report_templates": client_fields["report_templates"],
        "client_fields": client_fields,
        "sections": sections,
        "formula_metrics": [
            {
                "key": formula.key,
                "label": formula.label,
                "expression": formula.expression,
                "description": formula.description,
                "position": formula.position,
            }
            for formula in test.formulas
        ],
    }


def custom_client_fields_from_flat_form(
    field_keys: list[str],
    field_labels: list[str],
    field_types: list[str],
    field_required: list[str],
    field_placeholders: list[str],
) -> list[dict]:
    lengths = {
        len(field_keys),
        len(field_labels),
        len(field_types),
        len(field_required),
        len(field_placeholders),
    }
    if len(lengths) != 1:
        raise HTTPException(status_code=400, detail="Invalid custom client fields payload")

    custom_fields: list[dict] = []
    used_keys: set[str] = set()
    for idx, label_raw in enumerate(field_labels):
        label = label_raw.strip()
        key_input = field_keys[idx].strip()
        field_type = field_types[idx].strip().lower() or "text"
        required = field_required[idx].strip().lower() in {"true", "1", "yes"}
        placeholder = field_placeholders[idx].strip()

        if not label and not key_input and not placeholder:
            continue
        if not label:
            raise HTTPException(
                status_code=400,
                detail=f"Custom field label is required in row {idx+1}",
            )
        if field_type not in ALLOWED_CUSTOM_FIELD_TYPES:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported custom field type '{field_type}' in row {idx+1}",
            )

        key = normalize_key(key_input or label, f"client_field_{idx+1}")
        if key in RESERVED_CUSTOM_KEYS:
            raise HTTPException(
                status_code=400,
                detail=f"Reserved custom field key '{key}' in row {idx+1}",
            )
        if key in used_keys:
            raise HTTPException(
                status_code=400,
                detail=f"Duplicate custom field key '{key}' in row {idx+1}",
            )
        used_keys.add(key)
        custom_fields.append(
            {
                "key": key,
                "label": label,
                "type": field_type,
                "required": required,
                "placeholder": placeholder,
            }
        )

    return custom_fields


def report_templates_from_flat_form(
    client_blocks: list[str],
    psychologist_blocks: list[str],
) -> dict[str, list[str]]:
    return normalize_report_templates(
        {
            "client": client_blocks,
            "psychologist": psychologist_blocks,
        }
    )


def formulas_from_flat_form(
    metric_keys: list[str],
    metric_labels: list[str],
    metric_expressions: list[str],
    metric_descriptions: list[str],
) -> list[dict]:
    lengths = {
        len(metric_keys),
        len(metric_labels),
        len(metric_expressions),
        len(metric_descriptions),
    }
    if len(lengths) != 1:
        raise HTTPException(status_code=400, detail="Invalid formula payload")

    formulas: list[dict] = []
    used_keys: set[str] = set()
    for idx, raw_expression in enumerate(metric_expressions):
        expression = raw_expression.strip()
        label = metric_labels[idx].strip()
        input_key = metric_keys[idx].strip()
        description = metric_descriptions[idx].strip()

        if not expression and not label and not input_key and not description:
            continue
        if not expression:
            raise HTTPException(status_code=400, detail=f"Formula expression is required in row {idx+1}")

        key = normalize_key(input_key or label, f"metric_{idx+1}")
        if key in used_keys:
            raise HTTPException(status_code=400, detail=f"Duplicate formula key: {key}")
        used_keys.add(key)
        formulas.append(
            {
                "key": key,
                "label": label or key,
                "expression": expression,
                "description": description,
            }
        )
    return formulas


def sections_from_flat_form(
    section_titles: list[str],
    question_texts: list[str],
    question_types: list[str],
    question_required: list[str],
    question_options: list[str],
    question_min: list[str],
    question_max: list[str],
    question_weight: list[str],
    question_section_titles: list[str],
) -> list[dict]:
    unique_sections: OrderedDict[str, list] = OrderedDict()
    for title in section_titles:
        normalized = title.strip()
        if normalized:
            unique_sections.setdefault(normalized, [])

    size = len(question_texts)
    attrs = [
        question_types,
        question_required,
        question_options,
        question_min,
        question_max,
        question_weight,
        question_section_titles,
    ]
    if any(len(arr) != size for arr in attrs):
        raise HTTPException(status_code=400, detail="Invalid question form payload")

    for idx in range(size):
        text = question_texts[idx].strip()
        if not text:
            continue
        section_title = question_section_titles[idx].strip() or "General section"
        unique_sections.setdefault(section_title, [])
        q_type = question_types[idx].strip()
        required = question_required[idx].strip().lower() in {"true", "1", "yes"}
        options_json = parse_options(question_options[idx])
        min_value = None
        max_value = None
        try:
            if question_min[idx].strip():
                min_value = float(question_min[idx].strip())
            if question_max[idx].strip():
                max_value = float(question_max[idx].strip())
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid number range in question {idx+1}") from exc
        try:
            weight = float(question_weight[idx].strip() or "1")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=f"Invalid weight in question {idx+1}") from exc

        unique_sections[section_title].append(
            {
                "key": normalize_key(text, f"question_{idx+1}"),
                "text": text,
                "question_type": q_type,
                "required": required,
                "options_json": options_json,
                "min_value": min_value,
                "max_value": max_value,
                "weight": weight,
            }
        )

    result: list[dict] = []
    for title, questions in unique_sections.items():
        if questions:
            result.append({"title": title, "questions": questions})
    return result


