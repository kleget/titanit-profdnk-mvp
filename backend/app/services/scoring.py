from __future__ import annotations

from dataclasses import dataclass

from app.models import Question, QuestionType, Test


@dataclass
class ScoringResult:
    total_score: float
    max_score: float
    completion_percent: float
    answered_count: int
    total_questions: int

    def as_metrics(self) -> dict:
        percent_of_max = 0.0
        if self.max_score > 0:
            percent_of_max = round((self.total_score / self.max_score) * 100, 2)
        return {
            "total_score": round(self.total_score, 2),
            "max_score": round(self.max_score, 2),
            "score_percent": percent_of_max,
            "completion_percent": round(self.completion_percent, 2),
            "answered_count": self.answered_count,
            "total_questions": self.total_questions,
        }


def _numeric(value: object) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _is_empty(value: object) -> bool:
    return value is None or value == "" or (isinstance(value, list) and len(value) == 0)


def _max_option_score(question: Question) -> float:
    if not question.options_json:
        return question.weight
    best = 0.0
    for option in question.options_json:
        score = option.get("score", 0)
        try:
            best = max(best, float(score))
        except (TypeError, ValueError):
            continue
    return max(best * question.weight, question.weight)


def _score_for_choice(question: Question, answer: object) -> float:
    if question.question_type == QuestionType.YES_NO:
        if answer in {True, "true", "True", "1", 1, "yes", "on"}:
            return question.weight
        return 0.0

    if question.question_type == QuestionType.SINGLE_CHOICE:
        if answer is None or answer == "":
            return 0.0
        if not question.options_json:
            return question.weight
        for option in question.options_json:
            if str(option.get("value")) == str(answer):
                try:
                    return float(option.get("score", 1)) * question.weight
                except (TypeError, ValueError):
                    return question.weight
        return 0.0

    if question.question_type == QuestionType.MULTIPLE_CHOICE:
        if not answer:
            return 0.0
        selected = answer if isinstance(answer, list) else [answer]
        if not question.options_json:
            return float(len(selected)) * question.weight
        total = 0.0
        for option in question.options_json:
            if str(option.get("value")) in {str(v) for v in selected}:
                try:
                    total += float(option.get("score", 1))
                except (TypeError, ValueError):
                    total += 1
        return total * question.weight
    return 0.0


def _score_for_number_like(question: Question, answer: object) -> float:
    numeric = _numeric(answer)
    if numeric is None:
        return 0.0
    min_v = question.min_value if question.min_value is not None else 0.0
    max_v = question.max_value if question.max_value is not None else 10.0
    if max_v <= min_v:
        return max(0.0, numeric) * question.weight
    clamped = min(max(numeric, min_v), max_v)
    normalized = (clamped - min_v) / (max_v - min_v)
    return normalized * question.weight


def calculate_metrics(test: Test, answer_map: dict[int, object]) -> ScoringResult:
    total_questions = 0
    answered = 0
    total_score = 0.0
    max_score = 0.0

    for section in test.sections:
        for question in section.questions:
            total_questions += 1
            answer_value = answer_map.get(question.id)
            if not _is_empty(answer_value):
                answered += 1

            if question.question_type in {
                QuestionType.YES_NO,
                QuestionType.SINGLE_CHOICE,
                QuestionType.MULTIPLE_CHOICE,
            }:
                total_score += _score_for_choice(question, answer_value)
                if question.question_type == QuestionType.MULTIPLE_CHOICE and question.options_json:
                    max_score += (
                        sum(
                            float(option.get("score", 1))
                            for option in question.options_json
                            if option.get("score") is not None
                        )
                        * question.weight
                    )
                else:
                    max_score += _max_option_score(question)
            elif question.question_type in {
                QuestionType.NUMBER,
                QuestionType.SLIDER,
                QuestionType.RATING,
            }:
                total_score += _score_for_number_like(question, answer_value)
                max_score += question.weight
            else:
                # Non-numeric questions contribute only to completion.
                max_score += 0

    completion = 0.0
    if total_questions > 0:
        completion = (answered / total_questions) * 100

    return ScoringResult(
        total_score=total_score,
        max_score=max_score,
        completion_percent=completion,
        answered_count=answered,
        total_questions=total_questions,
    )
