"""Map a job title onto a role family.

Rules are ordered, first match wins, and the order matters more than any single
pattern: "React Native Developer" has to hit mobile before frontend, and
"Data Engineer" has to hit data before backend. Anything unmatched goes to
`other`, which is counted and reported rather than silently guessed at.
"""

from __future__ import annotations

import re

ROLE_FAMILIES = (
    "backend",
    "frontend",
    "fullstack",
    "data",
    "devops",
    "security",
    "qa",
    "mobile",
    "other",
)

_RULES: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"\b(mobile|android|ios|flutter|react[\s-]?native)\b"), "mobile"),
    (
        re.compile(
            r"\b(data engineer|data scientist|data analyst|analytics engineer|"
            r"machine learning|ml engineer|business intelligence|bi developer)\b"
        ),
        "data",
    ),
    (
        re.compile(
            r"\b(devops|dev ops|sre|site reliability|platform engineer|"
            r"infrastructure|cloud engineer)\b"
        ),
        "devops",
    ),
    (re.compile(r"\b(security|cyber|pentest|penetration|appsec|soc analyst)\b"), "security"),
    (
        re.compile(r"\b(qa|quality assurance|test engineer|sdet|automation tester)\b"),
        "qa",
    ),
    (re.compile(r"\b(full[\s-]?stack)\b"), "fullstack"),
    (
        re.compile(r"\b(frontend|front[\s-]end|react|vue|angular|ui engineer|ui/ux)\b"),
        "frontend",
    ),
    (
        re.compile(
            r"\b(backend|back[\s-]end|golang|go engineer|java engineer|php|laravel|"
            r"node\.?js|ruby on rails)\b"
        ),
        "backend",
    ),
)


def role_family(title: str) -> str:
    folded = " ".join(title.lower().split())
    for pattern, family in _RULES:
        if pattern.search(folded):
            return family
    return "other"
