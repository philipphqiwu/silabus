from __future__ import annotations

import pytest

from silabus.normalize.urls import canonicalize_url


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        # trailing slash collapsed
        (
            "https://boards.greenhouse.io/acme/jobs/123/",
            "https://boards.greenhouse.io/acme/jobs/123",
        ),
        # host lowercased, path left alone (paths can be case-sensitive)
        (
            "https://Jobs.Lever.CO/Acme/abc-123",
            "https://jobs.lever.co/Acme/abc-123",
        ),
        # tracking parameters stripped, the identifier survives
        (
            "https://boards.greenhouse.io/acme/jobs/123?gh_jid=123&utm_source=linkedin"
            "&utm_campaign=x&fbclid=abc",
            "https://boards.greenhouse.io/acme/jobs/123?gh_jid=123",
        ),
        # fragment dropped
        (
            "https://apply.workable.com/acme/j/ABC123/#app",
            "https://apply.workable.com/acme/j/ABC123",
        ),
        # remaining parameters sorted, so order never creates a new row
        (
            "https://example.com/jobs/1?b=2&a=1",
            "https://example.com/jobs/1?a=1&b=2",
        ),
        # default ports dropped
        ("http://example.com:80/jobs/1", "http://example.com/jobs/1"),
        ("https://example.com:443/jobs/1", "https://example.com/jobs/1"),
        # non-default ports kept
        ("https://example.com:8443/jobs/1", "https://example.com:8443/jobs/1"),
        # root path preserved
        ("https://example.com", "https://example.com/"),
    ],
)
def test_canonicalize(raw: str, expected: str) -> None:
    assert canonicalize_url(raw) == expected


@pytest.mark.parametrize(
    "raw",
    [
        "https://boards.greenhouse.io/acme/jobs/123?utm_source=x&utm_medium=y/",
        "  https://example.com/jobs/1?a=1&b=2  ",
        "https://Example.com:443/jobs/1#top?utm_source=x",
    ],
)
def test_idempotent(raw: str) -> None:
    once = canonicalize_url(raw)
    assert canonicalize_url(once) == once


@pytest.mark.parametrize("raw", ["", "   ", "/jobs/1", "boards.greenhouse.io/acme"])
def test_rejects_non_absolute(raw: str) -> None:
    with pytest.raises(ValueError, match="URL"):
        canonicalize_url(raw)
