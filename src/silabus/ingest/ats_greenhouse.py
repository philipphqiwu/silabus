"""Greenhouse job boards.

Public endpoint, no auth: https://boards-api.greenhouse.io/v1/boards/<board>/jobs?content=true
The payload includes the full description as escaped HTML, so remember to
unescape before treating it as markup.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from silabus.ingest.base import PoliteClient, SourceJob

SOURCE = "greenhouse"
BOARD_URL = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"


def fetch_board(client: PoliteClient, board: str) -> Mapping[str, Any]:
    payload = client.get_json(BOARD_URL.format(board=board))
    if not isinstance(payload, Mapping):
        raise ValueError(f"unexpected Greenhouse payload for board {board!r}")
    return payload


def parse_board(payload: Mapping[str, Any], *, board: str) -> list[SourceJob]:
    raw_jobs = payload.get("jobs")
    if not isinstance(raw_jobs, list):
        raise ValueError("payload has no 'jobs' list")

    jobs: list[SourceJob] = []
    for raw in raw_jobs:
        if not isinstance(raw, Mapping):
            continue
        job = _parse_job(raw, board=board)
        if job is not None:
            jobs.append(job)
    return jobs


def _parse_job(raw: Mapping[str, Any], *, board: str) -> SourceJob | None:
    job_id = str(raw.get("id") or "").strip()
    url = str(raw.get("absolute_url") or "").strip()
    title = str(raw.get("title") or "").strip()
    if not job_id or not url or not title:
        return None

    location = raw.get("location")
    location_name = None
    if isinstance(location, Mapping):
        location_name = str(location.get("name") or "").strip() or None

    company = raw.get("company_name") or board
    posted = raw.get("first_published") or raw.get("updated_at")
    content = raw.get("content")

    return SourceJob(
        source=SOURCE,
        external_id=job_id,
        source_url=url,
        title=title,
        company=str(company).strip() or None,
        location=location_name,
        description_html=str(content) if isinstance(content, str) else None,
        posted_at_raw=str(posted) if posted else None,
        payload=dict(raw),
    )
