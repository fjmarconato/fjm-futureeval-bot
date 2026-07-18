"""Deterministic ensemble calibration used by the forecasting bot.

This module intentionally has no Metaculus or LLM dependencies. That keeps the
money-critical aggregation logic fast, testable, and reproducible.
"""

from __future__ import annotations

import math
import statistics
from collections.abc import Sequence


DEFAULT_MIN_PROBABILITY = 0.02


def clip_probability(
    probability: float,
    minimum: float = DEFAULT_MIN_PROBABILITY,
) -> float:
    """Keep log-score losses finite without hiding genuine strong evidence."""
    if not 0 < minimum < 0.5:
        raise ValueError("minimum must be between 0 and 0.5")
    if not math.isfinite(probability):
        raise ValueError("probability must be finite")
    return min(1.0 - minimum, max(minimum, probability))


def _logit(probability: float) -> float:
    probability = clip_probability(probability, minimum=1e-6)
    return math.log(probability / (1.0 - probability))


def _sigmoid(value: float) -> float:
    if value >= 0:
        inverse = math.exp(-value)
        return 1.0 / (1.0 + inverse)
    exponent = math.exp(value)
    return exponent / (1.0 + exponent)


def _median_absolute_deviation(values: Sequence[float]) -> float:
    median = statistics.median(values)
    return statistics.median(abs(value - median) for value in values)


def aggregate_binary_probabilities(
    probabilities: Sequence[float],
    minimum: float = DEFAULT_MIN_PROBABILITY,
) -> float:
    """Pool forecasts in log-odds space with disagreement-aware calibration.

    Independent agreement permits mild extremization. Strong disagreement
    instead pulls the aggregate toward 50%, limiting one-model overconfidence.
    """
    if not probabilities:
        raise ValueError("at least one probability is required")

    logits = [_logit(value) for value in probabilities]
    median_logit = statistics.median(logits)
    disagreement = _median_absolute_deviation(logits)

    if len(logits) < 3:
        calibration_factor = 1.0
    elif disagreement <= 0.20:
        calibration_factor = 1.12
    elif disagreement <= 0.55:
        calibration_factor = 1.05
    elif disagreement <= 1.00:
        calibration_factor = 1.0
    else:
        calibration_factor = 0.88

    return clip_probability(
        _sigmoid(median_logit * calibration_factor),
        minimum=minimum,
    )


def aggregate_option_probabilities(
    probability_rows: Sequence[Sequence[float]],
    minimum: float = 0.005,
) -> list[float]:
    """Geometrically pool multiple-choice forecasts and normalize them."""
    if not probability_rows:
        raise ValueError("at least one probability row is required")

    option_count = len(probability_rows[0])
    if option_count < 2:
        raise ValueError("multiple-choice forecasts need at least two options")
    if minimum * option_count >= 1:
        raise ValueError("minimum is too large for the number of options")

    normalized_rows: list[list[float]] = []
    for row in probability_rows:
        if len(row) != option_count:
            raise ValueError("all probability rows must have the same length")
        if any(not math.isfinite(value) or value < 0 for value in row):
            raise ValueError("option probabilities must be finite and non-negative")
        total = sum(row)
        if total <= 0:
            raise ValueError("each probability row must have positive mass")
        normalized_rows.append([value / total for value in row])

    option_log_means = [
        statistics.mean(math.log(max(row[index], 1e-6)) for row in normalized_rows)
        for index in range(option_count)
    ]
    row_disagreement = statistics.mean(
        statistics.pstdev(math.log(max(row[index], 1e-6)) for row in normalized_rows)
        for index in range(option_count)
    )

    if len(normalized_rows) < 3:
        calibration_factor = 1.0
    elif row_disagreement <= 0.45:
        calibration_factor = 1.08
    elif row_disagreement <= 0.90:
        calibration_factor = 1.0
    else:
        calibration_factor = 0.90

    pooled = [math.exp(value * calibration_factor) for value in option_log_means]
    pooled_total = sum(pooled)
    normalized = [value / pooled_total for value in pooled]

    # This mixture guarantees the floor and an exact total of one.
    remaining_mass = 1.0 - minimum * option_count
    return [minimum + remaining_mass * value for value in normalized]
