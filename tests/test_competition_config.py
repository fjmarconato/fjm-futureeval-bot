import os
import unittest
from unittest.mock import patch

from competition_config import (
    DEFAULT_FUTUREEVAL_TOURNAMENT_ID,
    configured_futureeval_tournament_id,
    validate_live_ensemble_configuration,
    validate_live_research_configuration,
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

    def test_live_publish_requires_explicit_research(self):
        for research_model in ("", "None", "no_research"):
            with self.subTest(research_model=research_model):
                with self.assertRaisesRegex(ValueError, "without an explicit research model"):
                    validate_live_research_configuration(
                        run_mode="tournament",
                        will_publish=True,
                        research_model=research_model,
                    )

    def test_dry_runs_and_test_area_allow_no_research(self):
        validate_live_research_configuration(
            run_mode="tournament", will_publish=False, research_model="no_research"
        )
        validate_live_research_configuration(
            run_mode="test_questions", will_publish=True, research_model="no_research"
        )

    def test_live_publish_accepts_configured_research_provider(self):
        validate_live_research_configuration(
            run_mode="tournament",
            will_publish=True,
            research_model="asknews/deep-research/medium-depth",
        )

    def test_live_smart_search_requires_exa_key_and_model(self):
        with self.assertRaisesRegex(ValueError, "EXA_API_KEY is required"):
            validate_live_research_configuration(
                run_mode="tournament",
                will_publish=True,
                research_model="smart-searcher/gemini/gemini-3.6-flash",
            )
        with self.assertRaisesRegex(ValueError, "must include a model name"):
            validate_live_research_configuration(
                run_mode="tournament",
                will_publish=True,
                research_model="smart-searcher/",
                has_exa_key=True,
            )
        validate_live_research_configuration(
            run_mode="tournament",
            will_publish=True,
            research_model="smart-searcher/gemini/gemini-3.6-flash",
            has_exa_key=True,
        )

    def test_live_publish_requires_enough_predictions_for_each_model(self):
        with self.assertRaisesRegex(ValueError, "every configured model"):
            validate_live_ensemble_configuration(
                run_mode="tournament",
                will_publish=True,
                forecast_models="model-a,model-b,model-c",
                predictions_per_research_report=2,
            )

    def test_live_publish_rejects_duplicate_ensemble_models(self):
        with self.assertRaisesRegex(ValueError, "duplicate model names"):
            validate_live_ensemble_configuration(
                run_mode="tournament",
                will_publish=True,
                forecast_models="model-a,model-a",
                predictions_per_research_report=2,
            )

    def test_dry_run_does_not_require_full_ensemble(self):
        validate_live_ensemble_configuration(
            run_mode="tournament",
            will_publish=False,
            forecast_models="model-a,model-b,model-c",
            predictions_per_research_report=1,
        )


if __name__ == "__main__":
    unittest.main()
