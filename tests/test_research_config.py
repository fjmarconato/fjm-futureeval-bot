import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from main import (
    build_research_searcher,
    format_direct_exa_research,
    run_smart_search_with_fallback,
    validate_smart_search_report,
)


class ResearchConfigTests(unittest.TestCase):
    def test_direct_search_requires_source_url_and_excerpt(self):
        sources = [
            SimpleNamespace(
                title="Official release",
                url="https://example.org/release",
                highlights=["Dated announcement"],
                readable_publish_date="2026-09-28",
            )
        ]
        report = format_direct_exa_research(sources)
        self.assertIn("Dated announcement", report)
        self.assertIn("https://example.org/release", report)
        self.assertIn("2026-09-28", report)
        with self.assertRaisesRegex(RuntimeError, "no usable sources"):
            format_direct_exa_research(
                [SimpleNamespace(url=None, highlights=["No citation"])]
            )

    def test_searcher_retries_transient_model_errors(self):
        searcher = build_research_searcher("gemini/gemini-3.6-flash")
        self.assertEqual(searcher.llm._RetryableModel__allowed_tries, 3)
        self.assertEqual(searcher.number_of_searches_to_run, 1)
        self.assertEqual(searcher.exa_searcher.num_results, 5)

    def test_empty_search_results_cannot_pass_as_research(self):
        for report in ("", "  ", "No search results found for the query"):
            with self.subTest(report=report):
                with self.assertRaises(RuntimeError):
                    validate_smart_search_report(report)

        validate_smart_search_report("A dated primary source supports this claim.")


class ResearchFallbackTests(unittest.IsolatedAsyncioTestCase):
    async def test_uses_direct_exa_when_both_llms_fail(self):
        failed = SimpleNamespace(invoke=AsyncMock(side_effect=RuntimeError("model unavailable")))
        source = SimpleNamespace(
            title="Official release",
            url="https://example.org/release",
            highlights=["Dated announcement"],
            readable_publish_date="2026-09-28",
        )
        direct_search = SimpleNamespace(invoke=AsyncMock(return_value=[source]))
        with (
            patch("main.build_research_searcher", return_value=failed) as build,
            patch("main.ExaSearcher", return_value=direct_search) as exa,
        ):
            result = await run_smart_search_with_fallback(
                "prompt", "gemini/primary", "gemini/fallback", "question title"
            )
        self.assertEqual(build.call_count, 2)
        exa.assert_called_once_with(
            include_text=False, include_highlights=True, num_results=5
        )
        direct_search.invoke.assert_awaited_once_with("question title")
        self.assertIn("Dated announcement", result)

    async def test_retries_empty_research_with_alternate_model(self):
        primary = SimpleNamespace(
            invoke=AsyncMock(return_value="No search results found for the query")
        )
        fallback = SimpleNamespace(invoke=AsyncMock(return_value="Dated primary source"))
        with patch(
            "main.build_research_searcher", side_effect=[primary, fallback]
        ) as build:
            result = await run_smart_search_with_fallback(
                "question", "gemini/primary", "gemini/fallback"
            )
        self.assertEqual(result, "Dated primary source")
        self.assertEqual(
            [call.args[0] for call in build.call_args_list],
            ["gemini/primary", "gemini/fallback"],
        )

    async def test_raises_if_both_research_models_fail(self):
        failed = SimpleNamespace(
            invoke=AsyncMock(side_effect=RuntimeError("unavailable"))
        )
        with patch("main.build_research_searcher", return_value=failed) as build:
            with self.assertRaisesRegex(RuntimeError, "unavailable"):
                await run_smart_search_with_fallback(
                    "question", "gemini/primary", "gemini/fallback"
                )
        self.assertEqual(build.call_count, 2)

    async def test_valid_primary_research_does_not_call_fallback(self):
        primary = SimpleNamespace(invoke=AsyncMock(return_value="Dated primary source"))
        with patch("main.build_research_searcher", return_value=primary) as build:
            await run_smart_search_with_fallback(
                "question", "gemini/primary", "gemini/fallback"
            )
        build.assert_called_once_with("gemini/primary")


if __name__ == "__main__":
    unittest.main()
