"""Workable job boards.

Public widget endpoint, no auth:
https://apply.workable.com/api/v1/widget/accounts/<account>?details=true

Descriptions arrive as plain HTML (not escaped), and `requirements` is a
separate HTML field that often holds the skill list, so both are concatenated.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from silabus.ingest.base import PoliteClient, SourceJob

SOURCE = "workable"
ACCOUNT_URL = "https://apply.workable.com/api/v1/widget/accounts/{account}?details=true"


def fetch_account(client: PoliteClient, account: str) -> Mapping[str, Any]:
    payload = client.get_json(ACCOUNT_URL.format(account=account))
    if not isinstance(payload, Mapping):
        raise ValueError(f"unexpected Workable payload for account {account!r}")
    return payload


def parse_account(payload: Mapping[str, Any], *, account: str) -> list[SourceJob]:
    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list):
        raise ValueError("payload has no 'jobs' list")

    company = str(payload.get("name") or account).strip() or None

    jobs: list[SourceJob] = []
    for raw in raw_jobs:
        if not isinstance(raw, Mapping):
            continue
        job = _parse_job(raw, account=account, company=company)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_job(raw: Mapping[str, Any], *, account: str, company: str | None) -> SourceJob | None:
    job_id = str(raw.get("shortcode") or raw.get("code") or "").strip()
    url = str(raw.get("url") or raw.get("shortlink") or "").strip()
    title = str(raw.get("title") or "").strip()
    if not job_id or not url or not title:
        return None

    description_parts = [
        part
        for part in (raw.get("description"), raw.get("requirements"))
        if isinstance(part, str) and part.strip()
    ]
    posted = raw.get("published_on") or raw.get("created_at")

    return SourceJob(
        source=SOURCE,
        external_id=job_id,
        source_url=url,
        title=title,
        company=company,
        location=_location(raw),
        description_html="\n".join(description_parts) or None,
        posted_at_raw=str(posted) if posted else None,
        payload={**dict(raw), "account": account},
    )


def _location(raw: Mapping[str, Any]) -> str | None:
    locations = raw.get("locations")
    first: Mapping[str, Any] = {}
    if isinstance(locations, list) and locations and isinstance(locations[0], Mapping):
        first = locations[0]

    parts = [
        first.get("city") or raw.get("city"),
        first.get("region") or raw.get("state"),
        first.get("country") or raw.get("country"),
    ]
    joined = ", ".join(str(part).strip() for part in parts if part)
    if not joined:
        joined = "Remote" if raw.get("telecommuting") else ""

    if raw.get("telecommuting"):
        return f"Remote, {joined}" if joined else "Remote"
    return joined or None
