"""Picking a source and loading its postings.

`fixtures` reads recorded payloads from data/fixtures so ingest can be tested
without the network. `greenhouse` talks to the real board endpoint.
"""

from __future__ import annotations

import json
from dataclasses import replace
from pathlib import Path

from silabus.ingest import ats_greenhouse, ats_workable
from silabus.ingest.base import USER_AGENT, PoliteClient, SourceJob

FIXTURE_GLOB = "greenhouse_*.json"


def load_jobs(
    source: str,
    *,
    board: str | None = None,
    fixture_dir: Path = Path("data/fixtures"),
) -> list[SourceJob]:
    if source == "fixtures":
        return _load_fixtures(fixture_dir, board=board)
    if source == "greenhouse":
        return _load_greenhouse(board)
    if source == "workable":
        return _load_workable(board)
    raise ValueError(f"unknown source {source!r}; use fixtures, greenhouse or workable")


def _load_fixtures(fixture_dir: Path, *, board: str | None) -> list[SourceJob]:
    paths = sorted(fixture_dir.glob(FIXTURE_GLOB))
    if board is not None:
        paths = [path for path in paths if path.stem == f"greenhouse_{board}"]
    if not paths:
        raise ValueError(f"no fixtures matching {FIXTURE_GLOB} in {fixture_dir}")

    jobs: list[SourceJob] = []
    for path in paths:
        board_name = path.stem.removeprefix("greenhouse_")
        payload = json.loads(path.read_text())
        parsed = ats_greenhouse.parse_board(payload, board=board_name)
        # Recorded payloads are labelled as such, so a fixture run can never be
        # mistaken for live data in the same table.
        jobs.extend(replace(job, source="fixtures") for job in parsed)
    return jobs


def _load_greenhouse(board: str | None) -> list[SourceJob]:
    if not board:
        raise ValueError("--board is required for the greenhouse source")
    with PoliteClient(user_agent=USER_AGENT, cache_dir=Path("data/raw/http_cache")) as client:
        payload = ats_greenhouse.fetch_board(client, board)
    return ats_greenhouse.parse_board(payload, board=board)


def _load_workable(board: str | None) -> list[SourceJob]:
    if not board:
        raise ValueError("--board is required for the workable source")
    with PoliteClient(user_agent=USER_AGENT, cache_dir=Path("data/raw/http_cache")) as client:
        payload = ats_workable.fetch_account(client, board)
    return ats_workable.parse_account(payload, account=board)
