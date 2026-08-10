import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from question_selection import select_questions_for_run


def question(question_id: int, forecasted: bool, age_hours: float | None = None):
    previous_forecasts = None
    if age_hours is not None:
        previous_forecasts = [
            SimpleNamespace(
                timestamp=datetime.now(timezone.utc) - timedelta(hours=age_hours)
            )
        ]
    return SimpleNamespace(
        id_of_post=question_id,
        already_forecasted=forecasted,
        previous_forecasts=previous_forecasts,
    )


class QuestionSelectionTests(unittest.TestCase):
    def test_new_questions_are_always_prioritized(self):
        questions = [question(1, True, 72), question(2, False), question(3, False)]
        selected = select_questions_for_run(
            questions,
            skip_previously_forecasted=True,
            max_questions=2,
            refresh_after_hours=24,
        )
        self.assertEqual([item.id_of_post for item in selected], [2, 3])

    def test_refresh_selects_oldest_stale_forecasts(self):
        questions = [
            question(1, True, 30),
            question(2, True, 80),
            question(3, True, 10),
        ]
        selected = select_questions_for_run(
            questions,
            skip_previously_forecasted=True,
            max_questions=1,
            refresh_after_hours=24,
        )
        self.assertEqual([item.id_of_post for item in selected], [2])

    def test_refresh_disabled_preserves_current_behavior(self):
        selected = select_questions_for_run(
            [question(1, True, 72), question(2, False)],
            skip_previously_forecasted=True,
            max_questions=3,
        )
        self.assertEqual([item.id_of_post for item in selected], [2])

if __name__ == "__main__":
    unittest.main()
