"""Restrict bot subprocess credentials to the configured model providers."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Mapping

MODEL_ENV_NAMES = (
    "FORECAST_MODEL",
    "FORECAST_MODELS",
    "FALLBACK_FORECAST_MODEL",
    "PARSER_MODEL",
    "RESEARCH_MODEL",
    "FALLBACK_RESEARCH_MODEL",
    "MANUAL_FORECAST_MODEL_OVERRIDE",
    "MANUAL_RESEARCH_MODEL_OVERRIDE",
    "MANUAL_PARSER_MODEL_OVERRIDE",
    "NEXT_FORECAST_MODEL",
    "NEXT_RESEARCH_MODEL",
)

PROVIDER_SECRETS = {
    "openai": {"OPENAI_API_KEY"},
    "openrouter": {"OPENROUTER_API_KEY"},
    "anthropic": {"ANTHROPIC_API_KEY"},
    "google": {"GOOGLE_API_KEY"},
    "perplexity": {"PERPLEXITY_API_KEY"},
    "exa": {"EXA_API_KEY"},
    "asknews": {"ASKNEWS_CLIENT_ID", "ASKNEWS_SECRET"},
}

ALL_PROVIDER_SECRETS = set().union(*PROVIDER_SECRETS.values())
PROVIDER_ALIASES = {
    "google": "google",
    "gemini": "google",
    "google_genai": "google",
    "openai": "openai",
    "openrouter": "openrouter",
    "anthropic": "anthropic",
    "perplexity": "perplexity",
}


def _provider_for_model(model: str) -> set[str] | None:
    model = model.strip().lower()
    if not model or model in {"none", "no_research"}:
        return set()

    providers: set[str] = set()
    if model.startswith("asknews/"):
        return {"asknews"}
    if model.startswith("smart-searcher/"):
        providers.add("exa")
        model = model.removeprefix("smart-searcher/")
    if model.startswith("grounded/"):
        model = model.removeprefix("grounded/")

    provider = model.split("/", 1)[0]
    if provider in PROVIDER_ALIASES:
        providers.add(PROVIDER_ALIASES[provider])
    elif provider.startswith(("gpt-", "o1", "o3", "o4")):
        providers.add("openai")
    elif provider.startswith("gemini-"):
        providers.add("google")
    elif provider.startswith("claude-"):
        providers.add("anthropic")
    else:
        return None
    return providers


def required_provider_secrets(env: Mapping[str, str]) -> set[str] | None:
    """Return the required provider secrets, or None for unknown model syntax."""
    models = [
        model.strip()
        for name in MODEL_ENV_NAMES
        for model in env.get(name, "").split(",")
        if model.strip()
    ]
    if not models:
        return None

    providers: set[str] = set()
    for model in models:
        model_providers = _provider_for_model(model)
        if model_providers is None:
            return None
        providers.update(model_providers)

    required = {secret for provider in providers for secret in PROVIDER_SECRETS[provider]}
    required.add("METACULUS_TOKEN")
    return required


def filter_provider_environment(env: Mapping[str, str]) -> tuple[dict[str, str], set[str] | None]:
    required = required_provider_secrets(env)
    if required is None:
        return dict(env), None
    filtered = {
        name: value
        for name, value in env.items()
        if name not in ALL_PROVIDER_SECRETS or name in required
    }
    return filtered, required


def main() -> int:
    command = sys.argv[1:]
    if not command:
        print("Usage: python provider_env_filter.py COMMAND [ARGS...]", file=sys.stderr)
        return 2

    child_env, required = filter_provider_environment(os.environ)
    if required is None:
        print("Provider secret filtering skipped: model provider is unspecified or unknown.", flush=True)
    else:
        providers = sorted(
            provider
            for provider, names in PROVIDER_SECRETS.items()
            if names & required
        )
        print(f"Provider credentials enabled: {', '.join(providers)}", flush=True)

    return subprocess.run(command, env=child_env, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main())
