import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from provider_preflight import (
    ProviderAuthenticationError,
    record_authentication_block,
    validate_gemini_credentials,
)


class ProviderPreflightTests(unittest.TestCase):
    def setUp(self):
        self.env = {"FORECAST_MODEL": "gemini/example", "GOOGLE_API_KEY": "test-only"}

    @patch("provider_preflight.requests.get")
    def test_valid_key_uses_unbilled_metadata_endpoint_and_header(self, get):
        get.return_value.status_code = 200
        validate_gemini_credentials(self.env)
        get.assert_called_once_with(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"pageSize": 1},
            headers={"x-goog-api-key": "test-only"},
            timeout=20,
            allow_redirects=False,
        )

    @patch("provider_preflight.requests.get")
    def test_invalid_400_key_stops_without_exposing_response(self, get):
        get.return_value.status_code = 400
        get.return_value.json.return_value = {
            "error": {"details": [{"reason": "API_KEY_INVALID"}], "message": "private"}
        }
        with self.assertRaises(ProviderAuthenticationError) as caught:
            validate_gemini_credentials(self.env)
        self.assertNotIn("private", str(caught.exception))
        self.assertNotIn("test-only", str(caught.exception))
        get.assert_called_once()

    @patch("provider_preflight.requests.get")
    def test_missing_key_does_not_make_a_request(self, get):
        with self.assertRaises(ProviderAuthenticationError):
            validate_gemini_credentials({"PARSER_MODEL": "gemini/example"})
        get.assert_not_called()

    @patch("provider_preflight.requests.get")
    def test_authentication_and_permission_errors_are_permanent(self, get):
        for status in (401, 403):
            with self.subTest(status=status):
                get.return_value.status_code = status
                get.return_value.json.side_effect = ValueError("not JSON")
                with self.assertRaises(ProviderAuthenticationError):
                    validate_gemini_credentials(self.env)

    @patch("provider_preflight.requests.get")
    def test_optional_fallback_does_not_block_another_provider(self, get):
        validate_gemini_credentials({
            "FORECAST_MODEL": "openai/example",
            "FALLBACK_FORECAST_MODEL": "gemini/example",
        })
        get.assert_not_called()

    @patch("provider_preflight.requests.get")
    def test_ensemble_member_requires_key(self, get):
        with self.assertRaises(ProviderAuthenticationError):
            validate_gemini_credentials({"FORECAST_MODELS": "openai/a, gemini/b"})
        get.assert_not_called()

    @patch("provider_preflight.requests.get")
    def test_temporary_or_unexpected_errors_do_not_pause_auth_retries(self, get):
        for status in (429, 503, 302):
            with self.subTest(status=status):
                get.return_value.status_code = status
                get.return_value.json.return_value = {}
                with self.assertRaises(RuntimeError) as caught:
                    validate_gemini_credentials(self.env)
                self.assertNotIsInstance(caught.exception, ProviderAuthenticationError)
        get.side_effect = requests.Timeout("private request details")
        with self.assertRaisesRegex(RuntimeError, "could not reach Google") as caught:
            validate_gemini_credentials(self.env)
        self.assertNotIn("private", str(caught.exception))

    def test_block_is_reported_to_workflow_without_a_credential(self):
        with tempfile.TemporaryDirectory() as folder:
            output, summary = Path(folder) / "output", Path(folder) / "summary"
            with patch.dict(os.environ, {
                "GITHUB_OUTPUT": str(output), "GITHUB_STEP_SUMMARY": str(summary)
            }):
                record_authentication_block()
            self.assertEqual(output.read_text(), "provider_auth_blocked=true\n")
            self.assertIn("No research or forecasts were attempted", summary.read_text())


if __name__ == "__main__":
    unittest.main()
