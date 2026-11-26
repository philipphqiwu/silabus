"""Posted dates.

Only ISO timestamps are parsed. Anything else ("3 days ago", "Baru saja") is
kept as raw text and left as a null date rather than guessed at, because a
wrong posted_at silently corrupts any time series built on top of it.
"""

from __future__ import annotations

from datetime import date, datetime


def parse_posted_at(raw: str | None) -> date | None:
    if not raw:
        return None
    try:
        return datetime.fromisoformat(raw).date()
    except ValueError:
        return None
