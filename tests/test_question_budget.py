import os
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from forecasting_tools import ForecastBot

from main import FJMForecastBot2026


class QuestionBudgetTests(unittest.IsolatedAsyncioTestCase):
    async def test_limit_is_shared_across_tournaments(self):
        bot = object.__new__(FJMForecastBot2026)
        bot.skip_previously_forecasted_questions = True
        processed = []

        async def fake_forecast(_bot, questions, return_exceptions=False):
            processed.extend(question.id_of_post for question in questions)
            return questions

        def question(question_id):
            return SimpleNamespace(
                id_of_post=question_id,
                already_forecasted=False,
                previous_forecasts=None,
            )

        with patch.dict(os.environ, {"MAX_QUESTIONS_PER_RUN": "3"}):
            with patch.object(ForecastBot, "forecast_questions", fake_forecast):
                main_reports = await bot.forecast_questions(
                    [question(1), question(2)], return_exceptions=True
                )
                mini_reports = await bot.forecast_questions(
                    [question(3), question(4)], return_exceptions=True
                )
                exhausted_reports = await bot.forecast_questions(
                    [question(5)], return_exceptions=True
                )

        self.assertEqual([item.id_of_post for item in main_reports], [1, 2])
        self.assertEqual([item.id_of_post for item in mini_reports], [3])
        self.assertEqual(exhausted_reports, [])
        self.assertEqual(processed, [1, 2, 3])


if __name__ == "__main__":
    unittest.main()
