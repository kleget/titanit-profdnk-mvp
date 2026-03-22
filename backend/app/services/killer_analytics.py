from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from math import sqrt
from statistics import median

from app.models import InviteLink, Submission, Test


@dataclass
class _SubmissionAnalyticsRow:
    submission_id: int
    client_full_name: str
    source_label: str
    submitted_at: datetime
    score_percent: float
    completion_percent: float
    age: int | None
    custom_fields: dict[str, str]
    metrics: dict[str, float]
    formula_context: dict[str, float]


def _safe_float(value: object) -> float | None:
    if isinstance(value, bool):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        text = value.strip().replace(",", ".")
        if not text:
            return None
        try:
            return float(text)
        except ValueError:
            return None
    return None


def _safe_int(value: object) -> int | None:
    parsed = _safe_float(value)
    if parsed is None:
        return None
    if parsed < 0:
        return None
    return int(parsed)


def _submission_source_label(submission: Submission) -> str:
    extra = submission.client_extra_json or {}
    raw = extra.get("invite_label")
    if isinstance(raw, str) and raw.strip():
        return raw.strip()
    return "Основная ссылка"


def _extract_custom_fields(submission: Submission) -> dict[str, str]:
    extra = submission.client_extra_json or {}
    raw = extra.get("custom_fields")
    if not isinstance(raw, dict):
        return {}
    result: dict[str, str] = {}
    for key, value in raw.items():
        clean_key = str(key).strip()
        clean_value = str(value).strip()
        if clean_key and clean_value:
            result[clean_key] = clean_value
    return result


def _extract_formula_context(submission: Submission) -> dict[str, float]:
    metrics = submission.metrics_json or {}
    raw_context = metrics.get("formula_context")
    if not isinstance(raw_context, dict):
        return {}
    result: dict[str, float] = {}
    for key, value in raw_context.items():
        clean_key = str(key).strip()
        parsed = _safe_float(value)
        if clean_key and parsed is not None:
            result[clean_key] = parsed
    return result


def _scale_to_percent(value: float) -> float:
    if 0 <= value <= 1:
        return value * 100
    if -1 <= value <= 1:
        return (value + 1) * 50
    if -10 <= value <= 10:
        return value * 10
    return value


def _clamp_percent(value: float) -> float:
    return max(0.0, min(100.0, value))


def _mean(values: list[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / len(values)


def _stddev(values: list[float]) -> float:
    if len(values) < 2:
        return 0.0
    avg = _mean(values)
    variance = sum((item - avg) ** 2 for item in values) / len(values)
    return sqrt(variance)


def _percentile(sorted_values: list[float], value: float) -> float:
    if not sorted_values:
        return 0.0
    less_or_equal = sum(1 for item in sorted_values if item <= value)
    return round((less_or_equal / len(sorted_values)) * 100, 2)


def _build_rows(
    test: Test,
    submissions: list[Submission],
) -> tuple[list[_SubmissionAnalyticsRow], list[str]]:
    formula_keys = [formula.key for formula in sorted(test.formulas, key=lambda row: row.position)]
    metric_keys = ["score_percent", "completion_percent", "total_score", *formula_keys]

    rows: list[_SubmissionAnalyticsRow] = []
    for submission in submissions:
        metrics_json = submission.metrics_json or {}
        metrics: dict[str, float] = {}
        for key in metric_keys:
            parsed = _safe_float(metrics_json.get(key))
            if parsed is not None:
                metrics[key] = round(parsed, 4)
        score_percent = _safe_float(metrics_json.get("score_percent")) or 0.0
        completion_percent = _safe_float(metrics_json.get("completion_percent")) or 0.0
        age = _safe_int((submission.client_extra_json or {}).get("age"))
        rows.append(
            _SubmissionAnalyticsRow(
                submission_id=submission.id,
                client_full_name=submission.client_full_name,
                source_label=_submission_source_label(submission),
                submitted_at=submission.submitted_at,
                score_percent=round(score_percent, 2),
                completion_percent=round(completion_percent, 2),
                age=age,
                custom_fields=_extract_custom_fields(submission),
                metrics=metrics,
                formula_context=_extract_formula_context(submission),
            )
        )
    return rows, metric_keys


def _build_source_dynamics(rows: list[_SubmissionAnalyticsRow]) -> dict[str, object]:
    by_source_day: dict[tuple[str, str], dict[str, float]] = {}
    daily_totals: dict[str, int] = {}
    sources: set[str] = set()
    for row in rows:
        day = row.submitted_at.date().isoformat()
        key = (row.source_label, day)
        sources.add(row.source_label)
        if key not in by_source_day:
            by_source_day[key] = {
                "count": 0,
                "score_sum": 0.0,
                "score_count": 0,
                "completion_sum": 0.0,
                "completion_count": 0,
            }
        bucket = by_source_day[key]
        bucket["count"] += 1
        bucket["score_sum"] += row.score_percent
        bucket["score_count"] += 1
        bucket["completion_sum"] += row.completion_percent
        bucket["completion_count"] += 1
        daily_totals[day] = daily_totals.get(day, 0) + 1

    timeline_rows: list[dict[str, object]] = []
    for (source_label, day), bucket in sorted(by_source_day.items(), key=lambda item: (item[0][1], item[0][0])):
        avg_score = (
            round(bucket["score_sum"] / bucket["score_count"], 2) if bucket["score_count"] > 0 else None
        )
        avg_completion = (
            round(bucket["completion_sum"] / bucket["completion_count"], 2)
            if bucket["completion_count"] > 0
            else None
        )
        timeline_rows.append(
            {
                "source_label": source_label,
                "date": day,
                "count": int(bucket["count"]),
                "avg_score_percent": avg_score,
                "avg_completion_percent": avg_completion,
            }
        )

    daily_rows = [
        {"date": day, "count": count}
        for day, count in sorted(daily_totals.items(), key=lambda item: item[0])
    ]
    return {
        "timeline_rows": timeline_rows,
        "daily_rows": daily_rows,
        "sources": sorted(sources),
    }


def _build_audience_portrait(rows: list[_SubmissionAnalyticsRow]) -> dict[str, object]:
    age_buckets = {
        "до 15": 0,
        "16-18": 0,
        "19-25": 0,
        "26-35": 0,
        "36+": 0,
        "нет данных": 0,
    }
    level_buckets = {
        "низкий (0-44)": 0,
        "средний (45-69)": 0,
        "высокий (70+)": 0,
    }
    source_distribution: dict[str, int] = {}
    custom_fields_distribution: dict[str, dict[str, int]] = {}

    for row in rows:
        if row.age is None:
            age_buckets["нет данных"] += 1
        elif row.age <= 15:
            age_buckets["до 15"] += 1
        elif row.age <= 18:
            age_buckets["16-18"] += 1
        elif row.age <= 25:
            age_buckets["19-25"] += 1
        elif row.age <= 35:
            age_buckets["26-35"] += 1
        else:
            age_buckets["36+"] += 1

        score = row.score_percent
        if score < 45:
            level_buckets["низкий (0-44)"] += 1
        elif score < 70:
            level_buckets["средний (45-69)"] += 1
        else:
            level_buckets["высокий (70+)"] += 1

        source_distribution[row.source_label] = source_distribution.get(row.source_label, 0) + 1

        for key, value in row.custom_fields.items():
            custom_fields_distribution.setdefault(key, {})
            custom_fields_distribution[key][value] = custom_fields_distribution[key].get(value, 0) + 1

    top_custom_fields = []
    for field_key, values_map in custom_fields_distribution.items():
        top_values = sorted(values_map.items(), key=lambda item: item[1], reverse=True)[:3]
        top_custom_fields.append(
            {
                "field_key": field_key,
                "top_values": [{"value": value, "count": count} for value, count in top_values],
            }
        )

    return {
        "total_submissions": len(rows),
        "age_buckets": [{"label": label, "count": count} for label, count in age_buckets.items()],
        "level_buckets": [{"label": label, "count": count} for label, count in level_buckets.items()],
        "source_distribution": [
            {"label": label, "count": count}
            for label, count in sorted(source_distribution.items(), key=lambda item: item[1], reverse=True)
        ],
        "top_custom_fields": top_custom_fields,
    }


def _build_normalization(rows: list[_SubmissionAnalyticsRow], metric_keys: list[str]) -> dict[str, object]:
    values_by_key: dict[str, list[float]] = {key: [] for key in metric_keys}
    for row in rows:
        for key in metric_keys:
            value = row.metrics.get(key)
            if value is not None:
                values_by_key[key].append(float(value))

    stats_by_key: dict[str, dict[str, float]] = {}
    for key, values in values_by_key.items():
        if not values:
            continue
        stats_by_key[key] = {
            "mean": round(_mean(values), 4),
            "std": round(_stddev(values), 6),
            "median": round(float(median(values)), 4),
        }

    normalized_rows: list[dict[str, object]] = []
    for row in rows:
        metrics: dict[str, dict[str, float | None]] = {}
        for key, stats in stats_by_key.items():
            value = row.metrics.get(key)
            if value is None:
                metrics[key] = {
                    "value": None,
                    "z_score": None,
                    "percentile": None,
                    "median_delta": None,
                }
                continue
            sorted_values = sorted(values_by_key[key])
            std = stats["std"]
            z_score = 0.0 if std == 0 else (value - stats["mean"]) / std
            percentile_value = _percentile(sorted_values, value)
            median_delta = value - stats["median"]
            metrics[key] = {
                "value": round(value, 2),
                "z_score": round(z_score, 2),
                "percentile": round(percentile_value, 2),
                "median_delta": round(median_delta, 2),
            }
        normalized_rows.append(
            {
                "submission_id": row.submission_id,
                "client_full_name": row.client_full_name,
                "source_label": row.source_label,
                "submitted_at": row.submitted_at,
                "metrics": metrics,
            }
        )

    return {
        "stats_by_key": stats_by_key,
        "rows": normalized_rows,
        "metric_keys": [key for key in metric_keys if key in stats_by_key],
    }


def _build_risk_and_anomalies(
    normalized: dict[str, object],
) -> tuple[dict[str, object], list[dict[str, object]], list[dict[str, object]]]:
    rows = normalized["rows"]
    risk_rows: list[dict[str, object]] = []
    anomalies: list[dict[str, object]] = []
    zone_counters = {"high": 0, "medium": 0, "low": 0}

    for row in rows:
        metrics = row["metrics"]
        score = metrics.get("score_percent", {}).get("value")
        completion = metrics.get("completion_percent", {}).get("value")
        score_value = float(score) if isinstance(score, (int, float)) else 0.0
        completion_value = float(completion) if isinstance(completion, (int, float)) else 0.0
        resilience = round(score_value * 0.65 + completion_value * 0.35, 2)
        risk = round(100 - resilience, 2)
        if resilience >= 75:
            zone = "low"
            zone_label = "Низкий риск"
        elif resilience >= 55:
            zone = "medium"
            zone_label = "Средний риск"
        else:
            zone = "high"
            zone_label = "Высокий риск"
        zone_counters[zone] += 1

        risk_rows.append(
            {
                "submission_id": row["submission_id"],
                "client_full_name": row["client_full_name"],
                "source_label": row["source_label"],
                "submitted_at": row["submitted_at"],
                "resilience_index": resilience,
                "risk_index": risk,
                "zone": zone,
                "zone_label": zone_label,
            }
        )

        flags: list[str] = []
        if completion_value < 35:
            flags.append("низкая завершенность")
        for metric_key, value in metrics.items():
            z_score = value.get("z_score")
            if isinstance(z_score, (int, float)) and abs(z_score) >= 1.8:
                flags.append(f"выброс по {metric_key} (z={z_score:.2f})")
        if flags:
            anomalies.append(
                {
                    "submission_id": row["submission_id"],
                    "client_full_name": row["client_full_name"],
                    "source_label": row["source_label"],
                    "submitted_at": row["submitted_at"],
                    "flags": flags,
                }
            )

    return (
        {
            "rows": risk_rows,
            "zone_counters": zone_counters,
        },
        anomalies,
        risk_rows,
    )


def _collect_dimension_value(
    context: dict[str, float],
    fallback: float,
    keywords: tuple[str, ...],
) -> float:
    values = [
        _clamp_percent(_scale_to_percent(value))
        for key, value in context.items()
        if any(keyword in key.lower() for keyword in keywords)
    ]
    if values:
        return round(_mean(values), 2)
    return round(fallback, 2)


def _build_recommendations(
    rows: list[_SubmissionAnalyticsRow],
    risk_rows: list[dict[str, object]],
) -> list[dict[str, object]]:
    risk_by_submission = {row["submission_id"]: row for row in risk_rows}
    profession_profiles = [
        ("Аналитик данных", {"analytic": 0.65, "structure": 0.35}),
        ("QA-инженер", {"analytic": 0.5, "structure": 0.5}),
        ("Продуктовый менеджер", {"analytic": 0.35, "social": 0.35, "creative": 0.3}),
        ("Менеджер проектов", {"structure": 0.4, "social": 0.4, "practical": 0.2}),
        ("UX/UI-дизайнер", {"creative": 0.55, "social": 0.2, "analytic": 0.25}),
        ("HR / карьерный консультант", {"social": 0.7, "creative": 0.15, "structure": 0.15}),
    ]

    result: list[dict[str, object]] = []
    for row in rows:
        risk = risk_by_submission.get(row.submission_id)
        fallback_analytic = _clamp_percent(row.score_percent)
        fallback_structure = _clamp_percent(row.completion_percent)
        fallback_social = round((fallback_analytic + fallback_structure) / 2, 2)
        dimensions = {
            "analytic": _collect_dimension_value(
                row.formula_context,
                fallback_analytic,
                ("logic", "analysis", "math", "digital", "tech", "data"),
            ),
            "structure": _collect_dimension_value(
                row.formula_context,
                fallback_structure,
                ("stability", "discipline", "plan", "consistency", "completion", "order"),
            ),
            "social": _collect_dimension_value(
                row.formula_context,
                fallback_social,
                ("team", "social", "communication", "people", "client", "mentor"),
            ),
            "creative": _collect_dimension_value(
                row.formula_context,
                fallback_social,
                ("creative", "design", "art", "idea", "content"),
            ),
            "practical": _collect_dimension_value(
                row.formula_context,
                fallback_structure,
                ("project", "practice", "implementation", "hands", "action"),
            ),
        }

        scored = []
        for role_name, weights in profession_profiles:
            role_score = 0.0
            for key, weight in weights.items():
                role_score += dimensions[key] * weight
            scored.append((role_name, round(role_score, 2), weights))
        top_roles = sorted(scored, key=lambda item: item[1], reverse=True)[:3]
        top_dimension = sorted(dimensions.items(), key=lambda item: item[1], reverse=True)[:2]
        reason = ", ".join([f"{key}: {value:.1f}" for key, value in top_dimension])
        result.append(
            {
                "submission_id": row.submission_id,
                "client_full_name": row.client_full_name,
                "source_label": row.source_label,
                "risk_zone_label": risk["zone_label"] if risk else "-",
                "dimensions": dimensions,
                "recommendations": [
                    {"role": role_name, "score": role_score} for role_name, role_score, _weights in top_roles
                ],
                "reason": reason,
            }
        )
    return result


def build_killer_analytics(
    test: Test,
    submissions: list[Submission],
    invite_links_by_id: dict[int, InviteLink],  # noqa: ARG001 - для будущего расширения аналитики по ссылкам
) -> dict[str, object]:
    rows, metric_keys = _build_rows(test, submissions)
    if not rows:
        return {
            "has_data": False,
            "source_dynamics": {"timeline_rows": [], "daily_rows": [], "sources": []},
            "audience_portrait": {
                "total_submissions": 0,
                "age_buckets": [],
                "level_buckets": [],
                "source_distribution": [],
                "top_custom_fields": [],
            },
            "normalization": {"stats_by_key": {}, "rows": [], "metric_keys": []},
            "risk_overview": {"rows": [], "zone_counters": {"high": 0, "medium": 0, "low": 0}},
            "anomalies": [],
            "recommendations": [],
            "median_comparison_rows": [],
        }

    source_dynamics = _build_source_dynamics(rows)
    portrait = _build_audience_portrait(rows)
    normalization = _build_normalization(rows, metric_keys)
    risk_overview, anomalies, risk_rows = _build_risk_and_anomalies(normalization)
    recommendations = _build_recommendations(rows, risk_rows)

    stats_by_key = normalization["stats_by_key"]
    median_score = stats_by_key.get("score_percent", {}).get("median", 0.0)
    median_completion = stats_by_key.get("completion_percent", {}).get("median", 0.0)
    median_comparison_rows = []
    for row in normalization["rows"]:
        score = row["metrics"].get("score_percent", {}).get("value")
        completion = row["metrics"].get("completion_percent", {}).get("value")
        score_delta = (
            round(float(score) - float(median_score), 2) if isinstance(score, (int, float)) else None
        )
        completion_delta = (
            round(float(completion) - float(median_completion), 2)
            if isinstance(completion, (int, float))
            else None
        )
        median_comparison_rows.append(
            {
                "submission_id": row["submission_id"],
                "client_full_name": row["client_full_name"],
                "source_label": row["source_label"],
                "submitted_at": row["submitted_at"],
                "score_percent": score,
                "score_delta": score_delta,
                "completion_percent": completion,
                "completion_delta": completion_delta,
            }
        )

    return {
        "has_data": True,
        "source_dynamics": source_dynamics,
        "audience_portrait": portrait,
        "normalization": normalization,
        "risk_overview": risk_overview,
        "anomalies": anomalies,
        "recommendations": recommendations,
        "median_comparison_rows": median_comparison_rows,
    }
