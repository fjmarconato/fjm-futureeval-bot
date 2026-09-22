import os
import unittest
from unittest.mock import patch

from competition_config import (
    DEFAULT_FUTUREEVAL_TOURNAMENT_ID,
    configured_futureeval_tournament_id,
)


class CompetitionConfigTests(unittest.TestCase):
    def test_defaults_to_fall_2026(self):
        with patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                configured_futureeval_tournament_id(),
                DEFAULT_FUTUREEVAL_TOURNAMENT_ID,
            )

    def test_accepts_numeric_project_id(self):
        with patch.dict(os.environ, {"FUTUREEVAL_TOURNAMENT_ID": "33121"}):
            self.assertEqual(configured_futureeval_tournament_id(), 33121)

    def test_rejects_closed_summer_season(self):
        for closed_id in ("33022", "summer-futureeval-2026"):
            with self.subTest(closed_id=closed_id):
                with patch.dict(
                    os.environ, {"FUTUREEVAL_TOURNAMENT_ID": closed_id}
                ):
                    with self.assertRaisesRegex(ValueError, "closed season"):
                        configured_futureeval_tournament_id()


if __name__ == "__main__":
    unittest.main()
