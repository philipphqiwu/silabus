"""URL canonicalization.

`url_canonical` is the row identity for every source, so this runs before dedup
and before the UNIQUE constraint is checked. It has to be idempotent, and it
must not drop parameters that identify the posting (Greenhouse's `gh_jid`, for
example). Only known tracking parameters are removed.
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

TRACKING_PARAMS = frozenset(
    {
        "gclid",
        "fbclid",
        "mc_cid",
        "mc_eid",
        "msclkid",
        "yclid",
        "igshid",
        "_hsenc",
        "_hsmi",
        "ref_src",
        "ref_url",
        "lever-source",
        "lever-origin",
        "gh_src",
        "trk",
        "trkCampaign",
    }
)

TRACKING_PREFIXES = ("utm_", "hsa_", "pk_", "piwik_")


def _is_tracking(name: str) -> bool:
    lowered = name.lower()
    return lowered in TRACKING_PARAMS or lowered.startswith(TRACKING_PREFIXES)


def canonicalize_url(raw: str) -> str:
    """Return a stable identity URL for a job posting.

    - lowercases scheme and host, drops default ports
    - drops the fragment
    - removes tracking parameters, then sorts the rest
    - collapses a trailing slash (except for the root path)
    """
    candidate = raw.strip()
    if not candidate:
        raise ValueError("empty URL")

    parts = urlsplit(candidate)
    if parts.scheme.lower() not in {"http", "https"} or not parts.hostname:
        raise ValueError(f"not an absolute http(s) URL: {raw!r}")

    scheme = parts.scheme.lower()
    host = parts.hostname
    port = parts.port
    if port is not None and not (
        (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
    ):
        host = f"{host}:{port}"

    query = [
        (name, value)
        for name, value in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking(name)
    ]
    query.sort()

    path = parts.path or "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"

    return urlunsplit((scheme, host, path, urlencode(query), ""))
