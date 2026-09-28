import unittest

from main import build_research_searcher, validate_smart_search_report


class ResearchConfigTests(unittest.TestCase):
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


if __name__ == "__main__":
    unittest.main()
