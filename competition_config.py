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
