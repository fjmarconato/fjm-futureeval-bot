"""Read-only scan of the authenticated user's Metaculus comments for secrets."""

from __future__ import annotations

import os
import re
import sys
import time
from collections.abc import Iterator
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from math import log2
from typing import Any
from urllib.parse import urljoin

import requests

BASE_URL = "https://www.metaculus.com/api/"
PAGE_SIZE = 100
ARCHIVED_DETAIL_DELAY_SECONDS = 1.6
REQUEST_TIMEOUT_SECONDS = 20
MAX_RETRIES = 3
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
    for attempt in range(MAX_RETRIES + 1):
        try:
            response = session.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
        except requests.RequestException:
            if attempt == MAX_RETRIES:
                raise RuntimeError("Metaculus API connection failed after retries") from None
            time.sleep(_retry_delay(None, attempt))
            continue
        if response.status_code == 429 or response.status_code >= 500:
            if attempt == MAX_RETRIES:
                raise RuntimeError(f"Metaculus API request failed with HTTP {response.status_code} after retries")
            retry_after = response.headers.get("Retry-After")
            delay = _retry_delay(retry_after, attempt)
            time.sleep(delay)
            continue
        if not response.ok:
            raise RuntimeError(f"Metaculus API request failed with HTTP {response.status_code}")
        result = response.json()
        if not isinstance(result, dict):
            raise RuntimeError("Metaculus API returned an unexpected response")
        return result
    raise RuntimeError("Metaculus API retry loop ended unexpectedly")


def _retry_delay(retry_after: str | None, attempt: int) -> float:
    if retry_after:
        try:
            return min(120.0, max(1.0, float(retry_after)))
        except ValueError:
            try:
                retry_at = parsedate_to_datetime(retry_after)
                seconds = (retry_at - datetime.now(retry_at.tzinfo or timezone.utc)).total_seconds()
                return min(120.0, max(1.0, seconds))
            except (TypeError, ValueError, OverflowError):
                pass
    return min(120.0, float(2 ** (attempt + 1)))


def _comments(session: requests.Session, user_id: int, is_private: bool) -> Iterator[dict[str, Any]]:
    url = urljoin(BASE_URL, "comments/")
    seen_urls: set[str] = set()
    seen_ids: set[int] = set()
    page_number = 0
    params: dict[str, Any] | None = {
        "author": user_id,
        "is_private": str(is_private).lower(),
        "limit": PAGE_SIZE,
        "offset": 0,
    }
    while url:
        if url in seen_urls:
            visibility = "private" if is_private else "public"
            raise RuntimeError(f"Metaculus repeated the {visibility} comments pagination cursor")
        seen_urls.add(url)
        page = _get_json(session, url, params)
        params = None
        results = page.get("results")
        if not isinstance(results, list):
            raise RuntimeError("Metaculus API response omitted comment results")
        page_items = [item for item in results if isinstance(item, dict)]
        page_ids = [item.get("id") for item in page_items]
        valid_page_ids = [comment_id for comment_id in page_ids if isinstance(comment_id, int)]
        if valid_page_ids and all(comment_id in seen_ids for comment_id in valid_page_ids):
            visibility = "private" if is_private else "public"
            raise RuntimeError(f"Metaculus repeated a {visibility} comments page")
        seen_ids.update(valid_page_ids)
        page_number += 1
        visibility = "private" if is_private else "public"
        expected_total = page.get("count")
        print(
            f"Fetched {visibility} comments page {page_number}: {len(page_items)} records; "
            f"unique IDs {len(seen_ids)} of {expected_total if isinstance(expected_total, int) else 'unknown'}",
            flush=True,
        )
        yield from page_items
        next_url = page.get("next")
        if isinstance(expected_total, int) and len(seen_ids) >= expected_total:
            break
        if not page_items:
            raise RuntimeError(
                f"Metaculus returned an empty {visibility} comments page before the reported total"
            )
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


def _comment_text_for_scan(
    session: requests.Session, comment: dict[str, Any]
) -> tuple[str, bool]:
    try:
        return _full_comment_text(session, comment), False
    except RuntimeError:
        if not comment.get("is_text_archived"):
            raise
        prefix = comment.get("text")
        return (prefix if isinstance(prefix, str) else ""), True


def audit() -> tuple[int, list[dict[str, Any]], list[int]]:
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
    unresolved_archived_ids: list[int] = []
    for is_private in (False, True):
        for comment in _comments(session, user_id, is_private):
            comment_id = comment.get("id")
            if not isinstance(comment_id, int) or comment_id in scanned_ids:
                continue
            scanned_ids.add(comment_id)
            comment_text, unresolved = _comment_text_for_scan(session, comment)
            if unresolved:
                unresolved_archived_ids.append(comment_id)
            types = find_credential_types(comment_text)
            if types:
                findings.append({
                    "comment_id": comment_id,
                    "post_id": comment.get("on_post"),
                    "created_at": comment.get("created_at"),
                    "is_private": bool(comment.get("is_private", is_private)),
                    "detectors": types,
                })
            if len(scanned_ids) % 50 == 0:
                print(
                    f"Scanned {len(scanned_ids)} comments; "
                    f"archived details pending: {len(unresolved_archived_ids)}",
                    flush=True,
                )
    return len(scanned_ids), findings, unresolved_archived_ids


def main() -> int:
    try:
        scanned, findings, unresolved_archived_ids = audit()
    except Exception as exc:  # Keep response bodies, headers, and comment text out of logs.
        print(f"Audit failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1

    print(f"Comments scanned: {scanned}", flush=True)
    print(f"Potential credential-bearing comments: {len(findings)}", flush=True)
    print(f"Archived comments needing retry: {len(unresolved_archived_ids)}", flush=True)
    for comment_id in unresolved_archived_ids:
        print(f"Unresolved archived comment: comment_id={comment_id}", flush=True)
    for finding in findings:
        print(
            "Finding: "
            f"comment_id={finding['comment_id']} "
            f"post_id={finding['post_id']} "
            f"created_at={finding['created_at']} "
            f"private={finding['is_private']} "
            f"detectors={','.join(finding['detectors'])}",
            flush=True,
        )
    if not findings:
        print("No known credential patterns detected; this does not rule out unknown formats.", flush=True)
    return 2 if unresolved_archived_ids else 0


if __name__ == "__main__":
    raise SystemExit(main())
