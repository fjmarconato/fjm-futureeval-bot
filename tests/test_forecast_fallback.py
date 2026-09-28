import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from forecasting_tools import ForecastBot

from main import FJMForecastBot2026


class ForecastFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_primary_success_does_not_use_fallback(self):
        bot = object.__new__(FJMForecastBot2026)
        prediction = object()
        with (
            patch.dict(
                "os.environ",
                {
                    "FALLBACK_FORECAST_MODEL": "gemini/fallback",
                    "LLM_REQUEST_COOLDOWN_SECONDS": "0",
                },
            ),
            patch.object(FJMForecastBot2026, "get_llm", return_value="gemini/primary"),
            patch.object(FJMForecastBot2026, "set_llm") as set_llm,
            patch("main.build_forecast_llm") as build,
            patch.object(
                ForecastBot,
                "_make_prediction",
                new=AsyncMock(return_value=prediction),
            ) as make_prediction,
        ):
            result = await bot._make_prediction(SimpleNamespace(), "research")

        self.assertIs(result, prediction)
        make_prediction.assert_awaited_once()
        set_llm.assert_not_called()
        build.assert_not_called()

    async def test_tries_distinct_fallbacks_in_order(self):
        bot = object.__new__(FJMForecastBot2026)
        question = SimpleNamespace()
        prediction = object()
        failures = [RuntimeError("primary unavailable"), RuntimeError("first fallback unavailable")]
        with (
            patch.dict(
                "os.environ",
                {
                    "FALLBACK_FORECAST_MODEL": "gemini/primary, gemini/first, gemini/first, gemini/second",
                    "LLM_REQUEST_COOLDOWN_SECONDS": "0",
                },
            ),
            patch.object(FJMForecastBot2026, "get_llm", return_value="gemini/primary"),
            patch.object(FJMForecastBot2026, "set_llm") as set_llm,
            patch("main.build_forecast_llm", side_effect=lambda model, **_: model) as build,
            patch.object(
                ForecastBot,
                "_make_prediction",
                new=AsyncMock(side_effect=[*failures, prediction]),
            ) as make_prediction,
        ):
            result = await bot._make_prediction(question, "research")

        self.assertIs(result, prediction)
        self.assertEqual(make_prediction.await_count, 3)
        self.assertEqual(
            [call.args[0] for call in build.call_args_list],
            ["gemini/first", "gemini/second"],
        )
        self.assertEqual(set_llm.call_count, 2)

    async def test_raises_when_all_forecast_models_fail(self):
        bot = object.__new__(FJMForecastBot2026)
        with (
            patch.dict(
                "os.environ",
                {
                    "FALLBACK_FORECAST_MODEL": "gemini/fallback",
                    "LLM_REQUEST_COOLDOWN_SECONDS": "0",
                },
            ),
            patch.object(FJMForecastBot2026, "get_llm", return_value="gemini/primary"),
            patch.object(FJMForecastBot2026, "set_llm"),
            patch("main.build_forecast_llm", return_value="gemini/fallback"),
            patch.object(
                ForecastBot,
                "_make_prediction",
                new=AsyncMock(side_effect=[RuntimeError("primary"), RuntimeError("fallback")]),
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, "fallback"):
                await bot._make_prediction(SimpleNamespace(), "research")


if __name__ == "__main__":
    unittest.main()
