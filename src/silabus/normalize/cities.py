"""City and work-mode normalization.

Sources report locations as free text: "Jakarta Selatan, Indonesia",
"Remote - Indonesia", "Hybrid - Jakarta". The dashboard groups by city, so the
administrative detail is collapsed to the metro name and the raw value is kept
in `city_raw` for when that turns out to be the wrong call.
"""

from __future__ import annotations

import re

_REMOTE = re.compile(r"\b(remote|anywhere|work from home|wfh)\b", re.IGNORECASE)
_HYBRID = re.compile(r"\b(hybrid|partially remote)\b", re.IGNORECASE)
_SPLIT = re.compile(r"[,;(]|\s-\s")

_NOT_A_CITY = frozenset({"indonesia", "id", "remote", "anywhere", "asia", "apac"})

_ALIASES = {
    "jakarta": "Jakarta",
    "jakarta pusat": "Jakarta",
    "jakarta selatan": "Jakarta",
    "jakarta barat": "Jakarta",
    "jakarta timur": "Jakarta",
    "jakarta utara": "Jakarta",
    "dki jakarta": "Jakarta",
    "jkt": "Jakarta",
    "jabodetabek": "Jabodetabek",
    "jogja": "Yogyakarta",
    "yogya": "Yogyakarta",
    "yogyakarta": "Yogyakarta",
    "surabaja": "Surabaya",
    "ujung pandang": "Makassar",
}


def parse_location(raw: str | None) -> tuple[str | None, str]:
    """Return (city, work_mode). city is None when the source has no real city."""
    if not raw or not raw.strip():
        return None, "unknown"

    text = " ".join(raw.split())
    folded = text.lower()

    if _REMOTE.search(folded):
        work_mode = "remote"
    elif _HYBRID.search(folded):
        work_mode = "hybrid"
    else:
        work_mode = "onsite"

    # Drop the mode word before looking for a city, so "Hybrid - Jakarta" still
    # yields Jakarta instead of "Hybrid".
    city_text = _HYBRID.sub(" ", _REMOTE.sub(" ", text)).strip(" -,(;")
    first = _SPLIT.split(city_text)[0].strip(" -")
    folded_first = first.lower()

    if not first or folded_first in _NOT_A_CITY:
        return None, work_mode

    return _ALIASES.get(folded_first, first.title()), work_mode
