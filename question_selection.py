"""Dependency-free question selection for coverage and stale refresh runs."""

from datetime import datetime, timedelta, timezone
from typing import Any, Protocol, Sequence, TypeVar


class ForecastQuestion(Protocol):
    already_forecasted: bool | None
    previous_forecasts: list[Any] | None


QuestionT = TypeVar("QuestionT", bound=ForecastQuestion)


def _latest_forecast_time(question: ForecastQuestion) -> datetime | None:
    forecasts = question.previous_forecasts or []
    timestamps = [forecast.timestamp for forecast in forecasts if forecast.timestamp]
    if not timestamps:
        return None
    latest = max(timestamps)
    return latest if latest.tzinfo else latest.replace(tzinfo=timezone.utc)


def select_questions_for_run(
    questions: Sequence[QuestionT],
    *,
    skip_previously_forecasted: bool,
    max_questions: int | None,
    refresh_after_hours: float = 0,
    now: datetime | None = None,
) -> list[QuestionT]:
    """Prioritize uncovered questions, then the stalest eligible forecasts."""
    candidates = list(questions)
    if not skip_previously_forecasted:
        return candidates[:max_questions] if max_questions else candidates

    new_questions = [q for q in candidates if not q.already_forecasted]
    refresh_questions: list[tuple[datetime, QuestionT]] = []
    if refresh_after_hours > 0:
        cutoff = (now or datetime.now(timezone.utc)) - timedelta(
            hours=refresh_after_hours
        )
        for question in candidates:
            if not question.already_forecasted:
                continue
            latest = _latest_forecast_time(question)
            if latest is not None and latest <= cutoff:
                refresh_questions.append((latest, question))
        refresh_questions.sort(key=lambda item: item[0])

    selected = new_questions + [question for _, question in refresh_questions]
    return selected[:max_questions] if max_questions else selected
