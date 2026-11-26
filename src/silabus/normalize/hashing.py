"""Stable hashes used as row identity and as cache keys."""

from __future__ import annotations

import hashlib
import re

_WS = re.compile(r"\s+")


def _fold(text: str | None) -> str:
    if not text:
        return ""
    return _WS.sub(" ", text).strip().lower()


def content_hash(
    *,
    title: str,
    company: str | None,
    city: str | None,
    description: str,
) -> str:
    """Exact-duplicate key.

    Deliberately ignores source and URL so the same posting on two boards lands
    on the same hash. Only the head of the description is used; long postings
    usually differ in their trailing boilerplate.
    """
    parts = [_fold(title), _fold(company), _fold(city), _fold(description)[:4000]]
    return hashlib.sha256("\x1f".join(parts).encode()).hexdigest()


def description_hash(description: str) -> str:
    """Key for the LLM cache. Depends on the text only."""
    return hashlib.sha256(_fold(description).encode()).hexdigest()
