"""Seniority from titles.

Titles are the only field every source gives consistently, so this is title
only. A mention of "senior" in the description does not count, and postings
that say nothing get `unknown` rather than a guess.
"""

from __future__ import annotations

import re

LEVELS = ("intern", "junior", "mid", "senior", "lead", "unknown")

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(intern|internship|magang|apprentice)\b"), "intern"),
    (re.compile(r"\b(lead|principal|staff|head of|manager)\b"), "lead"),
    (re.compile(r"\b(senior|sr\.?|sr\b)\b"), "senior"),
    (re.compile(r"\b(junior|jr\.?|jr\b|entry|graduate|fresh grad)\b"), "junior"),
)


def seniority(title: str) -> str:
    folded = " ".join(title.lower().split())
    for pattern, level in _RULES:
        if pattern.search(folded):
            return level
    return "unknown"
