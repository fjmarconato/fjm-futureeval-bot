from provider_env_filter import filter_provider_environment


def test_gemini_smart_searcher_receives_only_required_provider_secrets():
    env = {
        "METACULUS_TOKEN": "metaculus-test",
        "GOOGLE_API_KEY": "google-test",
        "EXA_API_KEY": "exa-test",
        "OPENAI_API_KEY": "openai-test",
        "OPENROUTER_API_KEY": "openrouter-test",
        "ANTHROPIC_API_KEY": "anthropic-test",
        "PERPLEXITY_API_KEY": "perplexity-test",
        "ASKNEWS_SECRET": "asknews-test",
        "FORECAST_MODEL": "gemini/gemini-3.6-flash",
        "RESEARCH_MODEL": "smart-searcher/gemini/gemini-3.5-flash-lite",
        "FALLBACK_RESEARCH_MODEL": "gemini/gemini-3.5-flash",
    }

    filtered, required = filter_provider_environment(env)

    assert required == {"METACULUS_TOKEN", "GOOGLE_API_KEY", "EXA_API_KEY"}
    assert filtered["METACULUS_TOKEN"] == "metaculus-test"
    assert filtered["GOOGLE_API_KEY"] == "google-test"
    assert filtered["EXA_API_KEY"] == "exa-test"
    assert not (set(env) - set(filtered)) & {"FORECAST_MODEL", "RESEARCH_MODEL"}
    assert "OPENAI_API_KEY" not in filtered
    assert "OPENROUTER_API_KEY" not in filtered
    assert "ANTHROPIC_API_KEY" not in filtered
    assert "PERPLEXITY_API_KEY" not in filtered
    assert "ASKNEWS_SECRET" not in filtered


def test_mixed_models_and_manual_overrides_keep_each_provider():
    env = {
        "METACULUS_TOKEN": "metaculus-test",
        "GOOGLE_API_KEY": "google-test",
        "OPENAI_API_KEY": "openai-test",
        "OPENROUTER_API_KEY": "openrouter-test",
        "ANTHROPIC_API_KEY": "anthropic-test",
        "ASKNEWS_CLIENT_ID": "asknews-id-test",
        "ASKNEWS_SECRET": "asknews-secret-test",
        "FORECAST_MODELS": "gemini/gemini-3.6-flash,openai/gpt-5.6",
        "PARSER_MODEL": "openrouter/openai/gpt-4o-mini",
        "RESEARCH_MODEL": "asknews/news-summaries",
        "MANUAL_RESEARCH_MODEL_OVERRIDE": "anthropic/claude-3-7-sonnet",
    }

    filtered, required = filter_provider_environment(env)

    assert required == {
        "METACULUS_TOKEN",
        "GOOGLE_API_KEY",
        "OPENAI_API_KEY",
        "OPENROUTER_API_KEY",
        "ASKNEWS_CLIENT_ID",
        "ASKNEWS_SECRET",
        "ANTHROPIC_API_KEY",
    }
    assert set(filtered) == set(env)


def test_unknown_or_unspecified_model_syntax_fails_open():
    unknown = {
        "METACULUS_TOKEN": "metaculus-test",
        "GOOGLE_API_KEY": "google-test",
        "OPENAI_API_KEY": "openai-test",
        "FORECAST_MODEL": "new-provider/new-model",
    }
    empty = {"METACULUS_TOKEN": "metaculus-test", "GOOGLE_API_KEY": "google-test"}

    assert filter_provider_environment(unknown) == (unknown, None)
    assert filter_provider_environment(empty) == (empty, None)
