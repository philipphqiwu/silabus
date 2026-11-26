"""Ingest against a real database.

These are skipped when Postgres is not running, and run in CI where the
workflow starts one and applies the migrations first.
"""

from __future__ import annotations

from typing import Any

import psycopg
import pytest

from silabus.db import connect
from silabus.ingest.base import SourceJob
from silabus.ingest.runner import run_ingest
from silabus.ingest.sources import load_jobs


def _db_ready() -> bool:
    try:
        with connect() as conn:
            conn.execute("SELECT 1 FROM listings LIMIT 1")
    except psycopg.Error:
        return False
    return True


pytestmark = [
    pytest.mark.integration,
    pytest.mark.skipif(not _db_ready(), reason="postgres with migrations is not running"),
]


@pytest.fixture
def clean_fixtures() -> None:
    with connect() as conn:
        conn.execute("DELETE FROM raw_listings WHERE source = 'fixtures'")
        conn.execute("DELETE FROM listings WHERE source = 'fixtures'")


def _fixture_jobs() -> list[SourceJob]:
    return load_jobs("fixtures", board="acmenusantara")


def test_ingest_twice_does_not_duplicate(clean_fixtures: None) -> None:
    jobs = _fixture_jobs()

    first = run_ingest(jobs, source_name="fixtures")
    assert (first.fetched, first.inserted, first.errors) == (5, 5, 0)

    second = run_ingest(jobs, source_name="fixtures")
    assert (second.inserted, second.updated, second.errors) == (0, 5, 0)

    with connect() as conn:
        total = _scalar(conn, "SELECT count(*) FROM listings WHERE source = 'fixtures'")
        assert total == 5

        distinct_urls = _scalar(
            conn,
            "SELECT count(DISTINCT url_canonical) FROM listings WHERE source = 'fixtures'",
        )
        assert distinct_urls == 5


def test_every_listing_has_a_cluster(clean_fixtures: None) -> None:
    run_ingest(_fixture_jobs(), source_name="fixtures")

    with connect() as conn:
        unclustered = _scalar(conn, "SELECT count(*) FROM listings WHERE dedup_cluster_id IS NULL")
        not_self_clustered = _scalar(
            conn, "SELECT count(*) FROM listings WHERE dedup_cluster_id <> id"
        )

    assert unclustered == 0
    assert not_self_clustered == 0


def test_normalized_fields_land_in_the_columns(clean_fixtures: None) -> None:
    run_ingest(_fixture_jobs(), source_name="fixtures")

    with connect() as conn:
        row = conn.execute(
            """
            SELECT role_family, city, city_raw, seniority, work_mode, posted_at, description
            FROM listings
            WHERE source = 'fixtures' AND external_id = '9001'
            """
        ).fetchone()
        others = _scalar(
            conn,
            "SELECT count(*) FROM listings WHERE source = 'fixtures' AND role_family = 'other'",
        )

    assert row is not None
    role_family, city, city_raw, seniority, work_mode, posted_at, description = row
    assert role_family == "backend"
    assert city == "Jakarta"
    assert city_raw == "Jakarta Selatan, Indonesia"
    assert seniority == "unknown"
    assert work_mode == "onsite"
    assert posted_at.isoformat() == "2026-11-02"
    assert "<li>" not in description
    assert "Kafka" in description
    assert others == 1  # Product Designer


def test_contact_details_never_reach_raw_listings(clean_fixtures: None) -> None:
    run_ingest(_fixture_jobs(), source_name="fixtures")

    with connect() as conn:
        payloads = [
            str(row[0])
            for row in conn.execute(
                "SELECT payload::text FROM raw_listings WHERE source = 'fixtures'"
            ).fetchall()
        ]
        emails = _scalar(
            conn,
            "SELECT count(*) FROM raw_listings "
            "WHERE source = 'fixtures' AND payload::text LIKE '%@acme.example%'",
        )

    assert emails == 0
    joined = "\n".join(payloads)
    assert "812-3456-7890" not in joined
    assert "[email removed]" in joined or "[phone removed]" in joined


def test_ingest_run_is_recorded(clean_fixtures: None) -> None:
    run_ingest(_fixture_jobs(), source_name="fixtures")
    run_ingest(_fixture_jobs(), source_name="fixtures")

    with connect() as conn:
        rows = conn.execute(
            """
            SELECT fetched, inserted, errors
            FROM ingest_runs
            WHERE source = 'fixtures'
            ORDER BY id DESC
            LIMIT 2
            """
        ).fetchall()

    assert len(rows) == 2
    latest, previous = rows
    assert tuple(previous) == (5, 5, 0)
    assert tuple(latest) == (5, 0, 0)


def _scalar(conn: psycopg.Connection[Any], sql: str) -> Any:
    row = conn.execute(sql).fetchone()
    assert row is not None
    return row[0]
