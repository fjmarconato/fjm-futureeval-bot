from unittest.mock import Mock, patch

import requests

from audit_metaculus_comments import _get_json, find_credential_types


def test_detects_provider_key_formats_without_returning_values():
    samples = (
        ("GOOGLE_API_KEY=AIza" + "A" * 35, "google_api_key"),
        ("OPENAI_API_KEY=sk-proj-" + "B" * 24, "openai_api_key"),
        ("ANTHROPIC_API_KEY=sk-ant-" + "C" * 24, "anthropic_api_key"),
    )
    for comment, expected in samples:
        result = find_credential_types(comment)
        assert expected in result
        assert all(value not in result for value in (comment,))


def test_detects_generic_credential_assignment():
    assert "credential_assignment" in find_credential_types(
        '"api_key": "' + "xY7_" * 8 + '"'
    )


def test_detects_unknown_high_entropy_tokens():
    assert "generic_high_entropy_token" in find_credential_types(
        "token=" + "Ab9Xk2Pq7Lm4Rz8Vc3Nw6Ty1Hj5Df0Gs"
    )


def test_ignores_normal_comment_text():
    assert find_credential_types("The forecast is uncertain and needs more evidence.") == []


def test_retries_rate_limit_without_logging_response_body():
    limited = Mock(status_code=429, headers={"Retry-After": "2"}, ok=False)
    successful = Mock(status_code=200, headers={}, ok=True)
    successful.json.return_value = {"id": 1}
    session = Mock()
    session.get.side_effect = [limited, successful]

    with patch("audit_metaculus_comments.time.sleep") as sleep:
        assert _get_json(session, "https://www.metaculus.com/api/users/me") == {"id": 1}

    sleep.assert_called_once_with(2.0)


def test_retries_transient_connection_errors():
    successful = Mock(status_code=200, headers={}, ok=True)
    successful.json.return_value = {"id": 1}
    session = Mock()
    session.get.side_effect = [requests.ConnectionError("transient failure"), successful]

    with patch("audit_metaculus_comments.time.sleep") as sleep:
        assert _get_json(session, "https://www.metaculus.com/api/users/me") == {"id": 1}

    sleep.assert_called_once_with(2.0)
