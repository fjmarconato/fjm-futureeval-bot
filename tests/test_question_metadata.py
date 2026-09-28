import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from main import format_question_metadata


class QuestionMetadataTests(unittest.TestCase):
    def test_forecaster_rate_floor_uses_current_count_and_full_open_period(self):
        question = SimpleNamespace(
            page_url="https://www.metaculus.com/questions/45516",
            date_accessed=datetime(2026, 9, 27, tzinfo=timezone.utc),
            open_time=datetime(2026, 9, 6, tzinfo=timezone.utc),
            close_time=datetime(2026, 9, 28, tzinfo=timezone.utc),
            num_forecasters=244,
            resolution_criteria=(
                "number of forecasters listed in the Metaculus UI on the close "
                "date divided by the number of days this question is open"
            ),
        )
        metadata = format_question_metadata(question)
        self.assertIn("Current forecasters: 244", metadata)
        self.assertIn("Observed final-rate floor: 11.09 forecasters/day", metadata)

    def test_other_questions_do_not_get_forecaster_rate_floor(self):
        question = SimpleNamespace(
            page_url="https://www.metaculus.com/questions/1",
            date_accessed=datetime(2026, 9, 27, tzinfo=timezone.utc),
            open_time=None,
            close_time=None,
            num_forecasters=None,
            resolution_criteria="Will the event occur?",
        )
        metadata = format_question_metadata(question)
        self.assertIn("Current forecasters: unavailable", metadata)
        self.assertNotIn("Observed final-rate floor", metadata)


if __name__ == "__main__":
    unittest.main()
