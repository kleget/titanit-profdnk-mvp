from __future__ import annotations

import re
import secrets
from collections import OrderedDict

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models import Question, QuestionType, Test, TestSection


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
    sections_payload: list[dict],
) -> Test:
    if not title.strip():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Title is required")
    if not sections_payload:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one section required")

    required_fields = ["full_name"]
    required_fields.extend([field for field in required_client_fields if field != "full_name"])

    test = Test(
        psychologist_id=psychologist_id,
        title=title.strip(),
        description=description.strip(),
        allow_client_report=allow_client_report,
        required_client_fields=required_fields,
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

    db.commit()
    db.refresh(test)
    return test


def export_test_config(test: Test) -> dict:
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
        "required_client_fields": test.required_client_fields,
        "sections": sections,
    }


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
        section_title = question_section_titles[idx].strip() or "Общий раздел"
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

