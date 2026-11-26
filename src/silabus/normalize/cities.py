"""City and work-mode normalization.

Sources report locations as free text: "Jakarta Selatan, Indonesia",
"Remote - Indonesia", and often several cities at once:
"Bangkok, Thailand; Jakarta, Indonesia; Singapore, Singapore".

The dashboard groups by city, so the administrative detail is collapsed to the
metro name and the raw value is kept in `city_raw`. When a posting lists more
than one city it is counted once, under the first Indonesian city in the list.
That keeps an Indonesia-focused view from losing postings that are also open
elsewhere, at the cost of inflating the city that happens to be listed first.
Proper multi-location support would need its own table.
"""

from __future__ import annotations

import re

_REMOTE = re.compile(r"\b(remote|anywhere|work from home|wfh)\b", re.IGNORECASE)
_HYBRID = re.compile(r"\b(hybrid|partially remote)\b", re.IGNORECASE)
_GROUP_SPLIT = re.compile(r";|\s+or\s+", re.IGNORECASE)
_LABEL = re.compile(r"(?i)^location:\s*")

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
    # Workable reports the English names.
    "south jakarta": "Jakarta",
    "north jakarta": "Jakarta",
    "east jakarta": "Jakarta",
    "west jakarta": "Jakarta",
    "central jakarta": "Jakarta",
    "jakarta raya": "Jakarta",
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
    city = _pick_city(city_text)
    return city, work_mode


def _pick_city(city_text: str) -> str | None:
    groups = [group.strip(" -,(") for group in _GROUP_SPLIT.split(city_text)]
    groups = [group for group in groups if group]
    if not groups:
        return None

    candidates = [_LABEL.sub("", group.split(",")[0]).strip(" -,(") for group in groups]
    indonesian = [
        city for city, group in zip(candidates, groups, strict=True) if "indonesia" in group.lower()
    ]
    chosen = (indonesian or candidates)[0].lower()

    if not chosen or chosen in _NOT_A_CITY:
        return None
    return _ALIASES.get(chosen, chosen.title())
