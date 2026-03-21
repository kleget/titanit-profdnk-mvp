from __future__ import annotations

import re
from collections.abc import Iterable

BUILTIN_CLIENT_FIELDS = ("full_name", "email", "phone", "age")
OPTIONAL_BUILTIN_FIELDS = ("email", "phone", "age")
ALLOWED_CUSTOM_FIELD_TYPES = {"text", "textarea", "number", "date", "email", "phone"}
DEFAULT_CLIENT_REPORT_BLOCKS = (
    "profile",
    "summary_metrics",
    "charts",
    "derived_metrics",
    "answers",
)
DEFAULT_PSYCHOLOGIST_REPORT_BLOCKS = (
    "profile",
    "summary_metrics",
    "charts",
    "derived_metrics",
    "answers",
)
REPORT_BLOCK_LABELS = {
    "profile": "Данные клиента",
    "summary_metrics": "Ключевые показатели",
    "charts": "Визуализация метрик",
    "derived_metrics": "Производные метрики",
    "answers": "Ответы по методике",
}
ALLOWED_REPORT_BLOCKS = set(REPORT_BLOCK_LABELS)
RESERVED_CUSTOM_KEYS = {
    "full_name",
    "email",
    "phone",
    "age",
    "invite_label",
    "invite_token",
    "invite_link_id",
    "custom_fields",
}


def _normalize_key(source: str, fallback: str) -> str:
    prepared = re.sub(r"[^a-zA-Z0-9_]+", "_", source.strip().lower())
    prepared = re.sub(r"_+", "_", prepared).strip("_")
    return (prepared or fallback)[:64]


def _to_bool(value: object) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on", "да"}


def _normalize_required_builtin_fields(raw: Iterable[object] | None) -> list[str]:
    required = ["full_name"]
    if raw is None:
        return required
    for item in raw:
        field = str(item).strip().lower()
        if field in OPTIONAL_BUILTIN_FIELDS and field not in required:
            required.append(field)
    return required


def _normalize_custom_fields(raw: object) -> list[dict]:
    if not isinstance(raw, list):
        return []

    normalized: list[dict] = []
    used_keys: set[str] = set()
    for idx, item in enumerate(raw, start=1):
        if not isinstance(item, dict):
            continue

        label = str(item.get("label", "")).strip()
        if not label:
            continue

        key = _normalize_key(str(item.get("key", "")) or label, f"field_{idx}")
        if key in RESERVED_CUSTOM_KEYS:
            key = f"field_{key}"
        while key in used_keys:
            key = _normalize_key(f"{key}_{idx}", f"field_{idx}")
        used_keys.add(key)

        field_type = str(item.get("type", "text")).strip().lower()
        if field_type not in ALLOWED_CUSTOM_FIELD_TYPES:
            field_type = "text"

        placeholder = str(item.get("placeholder", "")).strip()[:200]
        normalized.append(
            {
                "key": key,
                "label": label[:120],
                "type": field_type,
                "required": _to_bool(item.get("required")),
                "placeholder": placeholder,
            }
        )

    return normalized[:20]


def _normalize_report_block_list(raw: object, default: tuple[str, ...]) -> list[str]:
    if not isinstance(raw, list):
        return list(default)
    prepared: list[str] = []
    for item in raw:
        key = str(item).strip()
        if key not in ALLOWED_REPORT_BLOCKS or key in prepared:
            continue
        prepared.append(key)
    return prepared or list(default)


def normalize_report_templates(raw_templates: object) -> dict[str, list[str]]:
    if not isinstance(raw_templates, dict):
        return {
            "client": list(DEFAULT_CLIENT_REPORT_BLOCKS),
            "psychologist": list(DEFAULT_PSYCHOLOGIST_REPORT_BLOCKS),
        }
    return {
        "client": _normalize_report_block_list(
            raw_templates.get("client"), DEFAULT_CLIENT_REPORT_BLOCKS
        ),
        "psychologist": _normalize_report_block_list(
            raw_templates.get("psychologist"), DEFAULT_PSYCHOLOGIST_REPORT_BLOCKS
        ),
    }


def normalize_client_fields_config(raw_config: object) -> dict[str, object]:
    if isinstance(raw_config, dict):
        required_source = raw_config.get("required_builtin_fields")
        if not isinstance(required_source, list):
            required_source = raw_config.get("required_client_fields")
        return {
            "required_builtin_fields": _normalize_required_builtin_fields(
                required_source if isinstance(required_source, list) else None
            ),
            "custom_fields": _normalize_custom_fields(
                raw_config.get("custom_fields") or raw_config.get("custom_client_fields")
            ),
            "report_templates": normalize_report_templates(raw_config.get("report_templates")),
        }

    if isinstance(raw_config, list):
        return {
            "required_builtin_fields": _normalize_required_builtin_fields(raw_config),
            "custom_fields": [],
            "report_templates": normalize_report_templates(None),
        }

    return {
        "required_builtin_fields": ["full_name"],
        "custom_fields": [],
        "report_templates": normalize_report_templates(None),
    }


def pack_client_fields_config(
    required_builtin_fields: list[str],
    custom_fields: list[dict] | None = None,
    report_templates: dict[str, list[str]] | None = None,
) -> dict[str, object]:
    return {
        "required_builtin_fields": _normalize_required_builtin_fields(required_builtin_fields),
        "custom_fields": _normalize_custom_fields(custom_fields or []),
        "report_templates": normalize_report_templates(report_templates),
    }


def build_client_form_fields(raw_config: object) -> list[dict]:
    config = normalize_client_fields_config(raw_config)
    required = set(config["required_builtin_fields"])
    custom_fields = list(config["custom_fields"])

    fields: list[dict] = [
        {
            "key": "email",
            "name": "client_email",
            "label": "Email",
            "input_type": "email",
            "required": "email" in required,
            "placeholder": "",
        },
        {
            "key": "phone",
            "name": "client_phone",
            "label": "Телефон",
            "input_type": "tel",
            "required": "phone" in required,
            "placeholder": "",
        },
        {
            "key": "age",
            "name": "client_age",
            "label": "Возраст",
            "input_type": "number",
            "required": "age" in required,
            "placeholder": "",
        },
    ]

    for field in custom_fields:
        input_type = str(field.get("type", "text"))
        html_type = "tel" if input_type == "phone" else input_type
        fields.append(
            {
                "key": field["key"],
                "name": f"client_custom_{field['key']}",
                "label": field["label"],
                "input_type": html_type,
                "required": bool(field.get("required", False)),
                "placeholder": str(field.get("placeholder", "")),
            }
        )
    return fields
