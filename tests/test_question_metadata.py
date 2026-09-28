import unittest
from datetime import datetime, timezone
from types import SimpleNamespace

from main import FJMForecastBot2026, format_question_metadata


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


class ForecastPromptMetadataTests(unittest.IsolatedAsyncioTestCase):
    async def test_all_nonbinary_forecast_prompts_include_question_metadata(self):
        async def capture_prompt(_question, prompt):
            return prompt

        forecaster = SimpleNamespace(
            _get_conditional_disclaimer_if_necessary=lambda _question: "",
            _create_upper_and_lower_bound_messages=lambda _question: ("lower", "upper"),
            _multiple_choice_prompt_to_forecast=capture_prompt,
            _numeric_prompt_to_forecast=capture_prompt,
            _date_prompt_to_forecast=capture_prompt,
        )
        common = dict(
            page_url="https://www.metaculus.com/questions/45516",
            date_accessed=datetime(2026, 9, 27, tzinfo=timezone.utc),
            open_time=datetime(2026, 9, 6, tzinfo=timezone.utc),
            close_time=datetime(2026, 9, 28, tzinfo=timezone.utc),
            num_forecasters=244,
            question_text="How many forecasters?",
            background_info="Background",
            fine_print="Fine print",
        )
        rate_criteria = (
            "number of forecasters listed in the Metaculus UI on the close "
            "date divided by the number of days this question is open"
        )
        multiple_choice = SimpleNamespace(
            **common, resolution_criteria="Which option?", options=["A", "B"]
        )
        numeric = SimpleNamespace(
            **common, resolution_criteria=rate_criteria, unit_of_measure="forecasters"
        )
        date = SimpleNamespace(**common, resolution_criteria="When?")

        cases = (
            (FJMForecastBot2026._run_forecast_on_multiple_choice, multiple_choice),
            (FJMForecastBot2026._run_forecast_on_numeric, numeric),
            (FJMForecastBot2026._run_forecast_on_date, date),
        )
        for forecast_method, question in cases:
            with self.subTest(method=forecast_method.__name__):
                prompt = await forecast_method(forecaster, question, "Evidence")
                self.assertIn(f"Question URL: {question.page_url}", prompt)
                self.assertIn("Current forecasters: 244", prompt)
                self.assertIn("Evidence", prompt)

        numeric_prompt = await FJMForecastBot2026._run_forecast_on_numeric(
            forecaster, numeric, "Evidence"
        )
        self.assertIn("Observed final-rate floor: 11.09", numeric_prompt)


if __name__ == "__main__":
    unittest.main()
