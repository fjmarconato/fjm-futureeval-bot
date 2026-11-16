import ast
from pathlib import Path


def test_forecast_bot_does_not_add_extra_metadata_to_explanations():
    source = Path(__file__).parents[1] / "main.py"
    tree = ast.parse(source.read_text(encoding="utf-8"))
    bot_calls = [
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "FJMForecastBot2026"
    ]

    assert len(bot_calls) == 1
    metadata_options = [
        keyword.value
        for keyword in bot_calls[0].keywords
        if keyword.arg == "extra_metadata_in_explanation"
    ]
    assert len(metadata_options) == 1
    assert isinstance(metadata_options[0], ast.Constant)
    assert metadata_options[0].value is False
