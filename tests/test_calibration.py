import math
import unittest

from calibration import (
    aggregate_binary_probabilities,
    aggregate_option_probabilities,
    clip_probability,
    constrain_numeric_values,
)


class CalibrationTests(unittest.TestCase):
    def test_clip_probability_limits_log_score_exposure(self) -> None:
        self.assertEqual(clip_probability(0.0), 0.02)
        self.assertEqual(clip_probability(1.0), 0.98)
        self.assertEqual(clip_probability(0.42), 0.42)

    def test_binary_pool_is_symmetric(self) -> None:
        positive = aggregate_binary_probabilities([0.70, 0.72, 0.74])
        negative = aggregate_binary_probabilities([0.30, 0.28, 0.26])
        self.assertAlmostEqual(positive, 1.0 - negative)

    def test_binary_consensus_is_mildly_extremized(self) -> None:
        result = aggregate_binary_probabilities([0.69, 0.70, 0.71])
        self.assertGreater(result, 0.70)
        self.assertLess(result, 0.75)

    def test_binary_disagreement_does_not_create_extreme_output(self) -> None:
        result = aggregate_binary_probabilities([0.08, 0.50, 0.92])
        self.assertAlmostEqual(result, 0.50)

    def test_multiple_choice_pool_is_normalized_and_floored(self) -> None:
        result = aggregate_option_probabilities(
            [
                [0.70, 0.20, 0.10],
                [0.65, 0.25, 0.10],
                [0.72, 0.18, 0.10],
            ]
        )
        self.assertTrue(math.isclose(sum(result), 1.0))
        self.assertGreaterEqual(min(result), 0.005)
        self.assertGreater(result[0], 0.70)

    def test_multiple_choice_rejects_mismatched_rows(self) -> None:
        with self.assertRaisesRegex(ValueError, "same length"):
            aggregate_option_probabilities([[0.5, 0.5], [0.3, 0.3, 0.4]])

    def test_numeric_values_stay_inside_sdk_validation_envelope(self) -> None:
        result = constrain_numeric_values(
            [15.3, 15.4, 16.2, 17.3],
            lower_bound=16.1,
            upper_bound=16.5,
        )
        self.assertGreater(result[0], 15.3)
        self.assertEqual(result[1:3], [15.4, 16.2])
        self.assertLess(result[3], 17.3)

    def test_numeric_values_respect_log_scale_zero_point(self) -> None:
        result = constrain_numeric_values(
            [-10.0, 2.0],
            lower_bound=1.0,
            upper_bound=5.0,
            zero_point=0.0,
        )
        self.assertGreater(result[0], 0.0)
        self.assertEqual(result[1], 2.0)

    def test_numeric_values_reject_invalid_bounds(self) -> None:
        with self.assertRaisesRegex(ValueError, "smaller"):
            constrain_numeric_values([1.0], lower_bound=2.0, upper_bound=2.0)


if __name__ == "__main__":
    unittest.main()
