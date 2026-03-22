from __future__ import annotations

import re


ALLOWED_LOGIC_OPERATORS = {
    "equals",
    "not_equals",
    "contains",
    "not_contains",
    "gt",
    "gte",
    "lt",
    "lte",
    "is_true",
    "is_false",
    "empty",
    "not_empty",
}

CONDITION_KEY_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def normalize_condition_payload(
    question_key_raw: str,
    operator_raw: str,
    value_raw: str,
) -> dict[str, str] | None:
    question_key = question_key_raw.strip()
    operator = operator_raw.strip().lower()
    value = value_raw.strip()

    if not question_key and not operator and not value:
        return None
    if not question_key:
        raise ValueError("Условие: не указан ключ вопроса")
    if not CONDITION_KEY_RE.fullmatch(question_key):
        raise ValueError(f"Условие: некорректный ключ вопроса '{question_key}'")
    if operator not in ALLOWED_LOGIC_OPERATORS:
        raise ValueError(f"Условие: неподдерживаемый оператор '{operator_raw}'")
    if operator not in {"is_true", "is_false", "empty", "not_empty"} and not value:
        raise ValueError("Условие: для выбранного оператора нужно значение")

    return {
        "question_key": question_key,
        "operator": operator,
        "value": value,
    }


def _is_empty(value: object) -> bool:
    return value is None or value == "" or (isinstance(value, list) and len(value) == 0)


def _to_number(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text:
        return None
    try:
        return float(text)
    except ValueError:
        return None


def _contains(actual: object, expected: str) -> bool:
    if isinstance(actual, list):
        normalized = {str(item).strip().lower() for item in actual}
        return expected.strip().lower() in normalized
    return expected.strip().lower() in str(actual or "").strip().lower()


def evaluate_condition(
    condition: dict | None,
    answers_by_key: dict[str, object],
) -> bool:
    if not condition:
        return True
    question_key = str(condition.get("question_key") or "").strip()
    operator = str(condition.get("operator") or "").strip().lower()
    expected = str(condition.get("value") or "").strip()
    actual = answers_by_key.get(question_key)

    if operator == "equals":
        return str(actual or "").strip().lower() == expected.lower()
    if operator == "not_equals":
        return str(actual or "").strip().lower() != expected.lower()
    if operator == "contains":
        return _contains(actual, expected)
    if operator == "not_contains":
        return not _contains(actual, expected)
    if operator == "gt":
        left = _to_number(actual)
        right = _to_number(expected)
        return left is not None and right is not None and left > right
    if operator == "gte":
        left = _to_number(actual)
        right = _to_number(expected)
        return left is not None and right is not None and left >= right
    if operator == "lt":
        left = _to_number(actual)
        right = _to_number(expected)
        return left is not None and right is not None and left < right
    if operator == "lte":
        left = _to_number(actual)
        right = _to_number(expected)
        return left is not None and right is not None and left <= right
    if operator == "is_true":
        return str(actual or "").strip().lower() in {"true", "1", "yes", "on"}
    if operator == "is_false":
        return str(actual or "").strip().lower() in {"false", "0", "no", "off"}
    if operator == "empty":
        return _is_empty(actual)
    if operator == "not_empty":
        return not _is_empty(actual)
    return True


def validate_condition_dependencies(
    *,
    question_keys_in_order: list[str],
    section_conditions: list[dict | None],
    question_conditions: list[dict | None],
    section_question_counts: list[int] | None = None,
) -> None:
    if len(question_keys_in_order) != len(question_conditions):
        raise ValueError("Некорректная структура условий: количество вопросов не совпадает.")

    known_keys: set[str] = set()
    section_sizes = section_question_counts or []
    if not section_sizes:
        section_sizes = [len(question_keys_in_order)]

    if len(section_sizes) != len(section_conditions):
        raise ValueError("Некорректная структура условий: не совпадает количество секций.")
    if sum(section_sizes) != len(question_keys_in_order):
        raise ValueError("Некорректная структура условий: не совпадает число вопросов по секциям.")

    question_position = 0
    for section_index, section_size in enumerate(section_sizes, start=1):
        section_condition = section_conditions[section_index - 1]
        if section_condition:
            dependency = str(section_condition.get("question_key") or "").strip()
            if dependency and dependency not in known_keys:
                raise ValueError(
                    f"Секция #{section_index}: условие ссылается на вопрос '{dependency}', "
                    "который объявлен ниже или отсутствует."
                )

        for _ in range(section_size):
            question_key = question_keys_in_order[question_position]
            question_condition = question_conditions[question_position]
            if question_condition:
                dependency = str(question_condition.get("question_key") or "").strip()
                if dependency and dependency not in known_keys:
                    raise ValueError(
                        f"Вопрос #{question_position + 1}: условие ссылается на вопрос '{dependency}', "
                        "который объявлен ниже или отсутствует."
                    )
            known_keys.add(question_key)
            question_position += 1
