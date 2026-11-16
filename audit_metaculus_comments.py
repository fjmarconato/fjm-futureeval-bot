"""Read-only scan of the authenticated user's Metaculus comments for secrets."""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Iterator
from math import log2
from typing import Any
from urllib.parse import urljoin

import requests

BASE_URL = "https://www.metaculus.com/api/"
PAGE_SIZE = 100
ARCHIVED_DETAIL_DELAY_SECONDS = 1.3
TOKEN_CANDIDATE = re.compile(r"(?<![A-Za-z0-9])[A-Za-z0-9_-]{32,128}(?![A-Za-z0-9])")

PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("google_api_key", re.compile(r"\bAIza[0-9A-Za-z_-]{30,}\b")),
    ("openai_api_key", re.compile(r"\bsk-(?:proj-|svcacct-)?[A-Za-z0-9_-]{20,}\b")),
    ("anthropic_api_key", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{20,}\b")),
    ("credential_assignment", re.compile(
        r"(?i)(?:api[_ -]?key|api[_ -]?token|secret(?:[_ -]?key)?|credential|password)"
        r"[\"']?\s*[:=]\s*[\"']?([A-Za-z0-9_+/=.-]{20,})"
    )),
)


def find_credential_types(text: str) -> list[str]:
    """Return detector names only; never return matched credential text."""
    matches = [name for name, pattern in PATTERNS if pattern.search(text)]
    if "generic_high_entropy_token" not in matches and any(
        _looks_like_token(match.group()) for match in TOKEN_CANDIDATE.finditer(text)
    ):
        matches.append("generic_high_entropy_token")
    return matches


def _looks_like_token(candidate: str) -> bool:
    if not any(char.isalpha() for char in candidate) or not any(char.isdigit() for char in candidate):
        return False
    frequencies = [candidate.count(char) / len(candidate) for char in set(candidate)]
    entropy = -sum(frequency * log2(frequency) for frequency in frequencies)
    return entropy >= 3.5


def _get_json(session: requests.Session, url: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = session.get(url, params=params, timeout=30)
    if not response.ok:
        raise RuntimeError(f"Metaculus API request failed with HTTP {response.status_code}")
    result = response.json()
    if not isinstance(result, dict):
        raise RuntimeError("Metaculus API returned an unexpected response")
    return result


def _comments(session: requests.Session, user_id: int, is_private: bool) -> Iterator[dict[str, Any]]:
    url = urljoin(BASE_URL, "comments/")
    params: dict[str, Any] | None = {
        "author": user_id,
        "is_private": str(is_private).lower(),
        "limit": PAGE_SIZE,
        "offset": 0,
    }
    while url:
        page = _get_json(session, url, params)
        params = None
        results = page.get("results")
        if not isinstance(results, list):
            raise RuntimeError("Metaculus API response omitted comment results")
        yield from (item for item in results if isinstance(item, dict))
        next_url = page.get("next")
        url = urljoin(BASE_URL, next_url) if isinstance(next_url, str) and next_url else ""


def _full_comment_text(session: requests.Session, comment: dict[str, Any]) -> str:
    text = comment.get("text")
    if not comment.get("is_text_archived"):
        return text if isinstance(text, str) else ""

    comment_id = comment.get("id")
    if not isinstance(comment_id, int):
        raise RuntimeError("Archived comment has no valid ID")
    time.sleep(ARCHIVED_DETAIL_DELAY_SECONDS)
    detail = _get_json(session, urljoin(BASE_URL, f"comments/{comment_id}/"))
    full_text = detail.get("text")
    if not isinstance(full_text, str):
        raise RuntimeError(f"Archived comment {comment_id} did not return full text")
    return full_text


def audit() -> tuple[int, list[dict[str, Any]]]:
    token = os.environ.get("METACULUS_TOKEN")
    if not token:
        raise RuntimeError("METACULUS_TOKEN is not configured")

    session = requests.Session()
    session.headers.update({"Authorization": f"Token {token}", "Accept": "application/json"})
    profile = _get_json(session, urljoin(BASE_URL, "users/me"))
    user_id = profile.get("id")
    if not isinstance(user_id, int):
        raise RuntimeError("Metaculus profile response omitted the user ID")

    scanned_ids: set[int] = set()
    findings: list[dict[str, Any]] = []
    for is_private in (False, True):
        for comment in _comments(session, user_id, is_private):
            comment_id = comment.get("id")
            if not isinstance(comment_id, int) or comment_id in scanned_ids:
                continue
            scanned_ids.add(comment_id)
            types = find_credential_types(_full_comment_text(session, comment))
            if types:
                findings.append({
                    "comment_id": comment_id,
                    "post_id": comment.get("on_post"),
                    "created_at": comment.get("created_at"),
                    "is_private": bool(comment.get("is_private", is_private)),
                    "detectors": types,
                })
    return len(scanned_ids), findings


def main() -> int:
    try:
        scanned, findings = audit()
    except Exception as exc:  # Keep response bodies, headers, and comment text out of logs.
        print(f"Audit failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Comments scanned: {scanned}")
    print(f"Potential credential-bearing comments: {len(findings)}")
    for finding in findings:
        print(
            "Finding: "
            f"comment_id={finding['comment_id']} "
            f"post_id={finding['post_id']} "
            f"created_at={finding['created_at']} "
            f"private={finding['is_private']} "
            f"detectors={','.join(finding['detectors'])}"
        )
    if not findings:
        print("No known credential patterns detected; this does not rule out unknown formats.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
