"""Check required provider credentials before spending research credits."""

import os
from collections.abc import Mapping
from pathlib import Path

import requests


class ProviderAuthenticationError(RuntimeError):
    """A required provider credential needs operator attention."""


def validate_gemini_credentials(environ: Mapping[str, str] | None = None) -> None:
    env = os.environ if environ is None else environ
    model_groups = (
        env.get("FORECAST_MODELS", "").strip()
        or env.get("FORECAST_MODEL", ""),
        env.get("PARSER_MODEL", ""),
    )
    if not any(
        model.strip().startswith("gemini/")
        for group in model_groups
        for model in group.split(",")
    ):
        return

    api_key = env.get("GEMINI_API_KEY") or env.get("GOOGLE_API_KEY")
    if not api_key or not api_key.strip():
        raise ProviderAuthenticationError("The required Gemini API key is missing.")

    # Listing models checks authentication without generating paid content.
    try:
        response = requests.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            params={"pageSize": 1},
            headers={"x-goog-api-key": api_key},
            timeout=20,
            allow_redirects=False,
        )
    except requests.RequestException:
        raise RuntimeError("Gemini credential preflight could not reach Google.") from None

    if response.status_code == 200:
        return
    try:
        error = response.json().get("error", {})
        details = error.get("details", [])
        invalid_key = any(
            isinstance(detail, dict) and detail.get("reason") == "API_KEY_INVALID"
            for detail in details
        )
    except (ValueError, AttributeError, TypeError):
        invalid_key = False
    if response.status_code in {401, 403} or invalid_key:
        raise ProviderAuthenticationError(
            "Google rejected the Gemini API key or its permissions. "
            "Restore the authorized free-tier credential in GOOGLE_API_KEY "
            "before resuming research and forecasts."
        )
    raise RuntimeError(
        f"Gemini credential preflight returned HTTP {response.status_code}; "
        "no research or forecasts were attempted."
    )


def record_authentication_block() -> None:
    output_path = os.getenv("GITHUB_OUTPUT")
    if output_path:
        with Path(output_path).open("a", encoding="utf-8") as output:
            output.write("provider_auth_blocked=true\n")
    summary_path = os.getenv("GITHUB_STEP_SUMMARY")
    if summary_path:
        with Path(summary_path).open("a", encoding="utf-8") as summary:
            summary.write(
                "\n## Forecasting blocked: Gemini authentication\n"
                "Google rejected the required credential. No research or forecasts "
                "were attempted. The chained retry is paused; the scheduled "
                "bootstrap will check again. Restore the authorized free-tier "
                "GOOGLE_API_KEY to resume.\n"
            )
