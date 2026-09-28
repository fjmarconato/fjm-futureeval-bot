"""Season-specific configuration and guards for competitive runs."""

from __future__ import annotations

import os


DEFAULT_FUTUREEVAL_TOURNAMENT_ID = "fall-futureeval-2026"
DEFAULT_FUTUREEVAL_TOURNAMENT_URL = (
    "https://www.metaculus.com/tournament/fall-futureeval-2026/"
)

_CLOSED_FUTUREEVAL_TOURNAMENTS = {
    "33022",
    "summer-futureeval-2026",
}


def configured_futureeval_tournament_id() -> int | str:
    """Return the explicitly configured live season, rejecting closed seasons."""
    raw_value = os.getenv(
        "FUTUREEVAL_TOURNAMENT_ID", DEFAULT_FUTUREEVAL_TOURNAMENT_ID
    ).strip()
    if not raw_value:
        raise ValueError("FUTUREEVAL_TOURNAMENT_ID cannot be empty")
    if raw_value.lower() in _CLOSED_FUTUREEVAL_TOURNAMENTS:
        raise ValueError(
            f"FUTUREEVAL_TOURNAMENT_ID points to closed season {raw_value!r}"
        )
    return int(raw_value) if raw_value.isdigit() else raw_value


def validate_live_research_configuration(
    *, run_mode: str, will_publish: bool, research_model: str, has_exa_key: bool = False
) -> None:
    """Refuse live tournament publishing when research is explicitly disabled."""
    if run_mode != "tournament" or not will_publish:
        return

    if research_model.strip().casefold() in {"", "none", "no_research"}:
        raise ValueError(
            "Refusing to publish live FutureEval forecasts without an explicit "
            "research model. Configure a tested research provider first."
        )
    if research_model.startswith("smart-searcher/"):
        if not research_model.removeprefix("smart-searcher/").strip():
            raise ValueError("smart-searcher/ must include a model name")
        if not has_exa_key:
            raise ValueError(
                "Refusing to publish: EXA_API_KEY is required for smart-searcher research"
            )


def validate_live_ensemble_configuration(
    *,
    run_mode: str,
    will_publish: bool,
    forecast_models: str,
    predictions_per_research_report: int,
) -> None:
    """Ensure a live ensemble uses every configured model on each question."""
    if run_mode != "tournament" or not will_publish:
        return

    models = [model.strip() for model in forecast_models.split(",") if model.strip()]
    if len(models) != len(set(models)):
        raise ValueError("FORECAST_MODELS must not contain duplicate model names")
    if len(models) > predictions_per_research_report:
        raise ValueError(
            "Refusing to publish: FORECAST_MODELS contains "
            f"{len(models)} models but PREDICTIONS_PER_RESEARCH_REPORT is "
            f"{predictions_per_research_report}; every configured model must "
            "contribute to each question."
        )
