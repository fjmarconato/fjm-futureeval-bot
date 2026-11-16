from unittest.mock import Mock, patch

import requests

from audit_metaculus_comments import _comment_text_for_scan, _comments, _get_json, find_credential_types


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


def test_archived_comment_failure_uses_prefix_and_marks_incomplete():
    comment = {"id": 42, "is_text_archived": True, "text": "truncated prefix"}
    with patch("audit_metaculus_comments._full_comment_text", side_effect=RuntimeError("unavailable")):
        text, unresolved = _comment_text_for_scan(Mock(), comment)

    assert text == "truncated prefix"
    assert unresolved is True


def test_unarchived_comment_failure_is_not_silently_skipped():
    comment = {"id": 42, "is_text_archived": False, "text": "ordinary comment"}
    with patch("audit_metaculus_comments._full_comment_text", side_effect=RuntimeError("unavailable")):
        try:
            _comment_text_for_scan(Mock(), comment)
        except RuntimeError as exc:
            assert str(exc) == "unavailable"
        else:
            raise AssertionError("expected the API error to propagate")


def test_comments_rejects_repeated_page_ids():
    page_items = [{"id": comment_id} for comment_id in range(100)]
    pages = [{"results": page_items}, {"results": page_items}]
    with patch("audit_metaculus_comments._get_json", side_effect=pages):
        try:
            list(_comments(Mock(), user_id=7, is_private=False))
        except RuntimeError as exc:
            assert "repeated a public comments page" in str(exc)
        else:
            raise AssertionError("expected repeated page IDs to fail")


def test_comments_stops_when_reported_total_is_reached():
    page = {
        "count": 1,
        "results": [{"id": 1}],
    }
    with patch("audit_metaculus_comments._get_json", return_value=page) as get_json:
        assert list(_comments(Mock(), user_id=7, is_private=False)) == [{"id": 1}]

    get_json.assert_called_once()


def test_comments_keeps_author_filter_on_every_page_and_stops_on_partial_page():
    full_page = [{"id": comment_id} for comment_id in range(100)]
    last_page = [{"id": 100}]
    session = Mock()
    with patch(
        "audit_metaculus_comments._get_json",
        side_effect=[{"results": full_page}, {"results": last_page}],
    ) as get_json:
        assert len(list(_comments(session, user_id=7, is_private=True))) == 101

    assert get_json.call_args_list[0].args[2] == {
        "author": 7, "is_private": "true", "limit": 100, "offset": 0
    }
    assert get_json.call_args_list[1].args[2] == {
        "author": 7, "is_private": "true", "limit": 100, "offset": 100
    }
