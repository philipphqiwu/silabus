"""Writing a batch of postings to Postgres.

The contract this module has to keep: running the same batch twice must not
create a second row for any posting. `listings` is keyed by `url_canonical`, and
`raw_listings` is keyed by (source, url_canonical, fetch_date), so both sides
absorb a repeat run.
"""

from __future__ import annotations

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime
from typing import Any

import psycopg
from psycopg.types.json import Jsonb

from silabus.db import connect
from silabus.ingest.base import SourceJob, scrub_payload
from silabus.ingest.transform import ListingRow, to_listing_row

log = logging.getLogger(__name__)

_INSERT_RAW = """
INSERT INTO raw_listings
    (run_id, source, source_url, url_canonical, fetch_date, fetched_at, payload)
VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (source, url_canonical, fetch_date) DO NOTHING
RETURNING id
"""

_INSERT_LISTING = """
INSERT INTO listings
    (source, external_id, source_url, url_canonical, title_raw, company,
     role_family, city, city_raw, seniority, work_mode, posted_at,
     posted_at_raw, description, content_hash, description_hash)
VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
RETURNING id
"""

_UPDATE_LISTING = """
UPDATE listings SET
    external_id      = %s,
    source_url       = %s,
    title_raw        = %s,
    company          = %s,
    role_family      = %s,
    city             = %s,
    city_raw         = %s,
    seniority        = %s,
    work_mode        = %s,
    posted_at        = %s,
    posted_at_raw    = %s,
    description      = %s,
    content_hash     = %s,
    description_hash = %s
WHERE url_canonical = %s
"""


@dataclass
class IngestStats:
    source: str
    fetched: int = 0
    inserted: int = 0
    updated: int = 0
    duplicates: int = 0
    errors: int = 0


def run_ingest(jobs: Iterable[SourceJob], *, source_name: str) -> IngestStats:
    stats = IngestStats(source=source_name)
    started_at = datetime.now(UTC)
    fetch_date = started_at.date()

    with connect() as conn:
        row = conn.execute(
            "INSERT INTO ingest_runs (source, started_at) VALUES (%s, %s) RETURNING id",
            (source_name, started_at),
        ).fetchone()
        if row is None:
            raise RuntimeError("could not create ingest_run")
        run_id = int(row[0])
        conn.commit()

        for job in jobs:
            stats.fetched += 1
            try:
                with conn.transaction():
                    _store_job(conn, run_id, job, fetch_date=fetch_date, stats=stats)
            except (ValueError, psycopg.Error) as exc:
                stats.errors += 1
                log.warning("skipping %s %s: %s", job.source, job.external_id, exc)

        conn.execute("UPDATE listings SET dedup_cluster_id = id WHERE dedup_cluster_id IS NULL")
        conn.execute(
            """
            UPDATE ingest_runs SET
                finished_at = %s, fetched = %s, inserted = %s,
                updated = %s, duplicates = %s, errors = %s
            WHERE id = %s
            """,
            (
                datetime.now(UTC),
                stats.fetched,
                stats.inserted,
                stats.updated,
                stats.duplicates,
                stats.errors,
                run_id,
            ),
        )

    return stats


def _store_job(
    conn: psycopg.Connection[Any],
    run_id: int,
    job: SourceJob,
    *,
    fetch_date: date,
    stats: IngestStats,
) -> None:
    listing = to_listing_row(job)

    raw = conn.execute(
        _INSERT_RAW,
        (
            run_id,
            job.source,
            job.source_url,
            listing.url_canonical,
            fetch_date,
            datetime.now(UTC),
            Jsonb(scrub_payload(job.payload)),
        ),
    ).fetchone()
    if raw is None:
        stats.duplicates += 1

    _upsert_listing(conn, listing, stats)


def _upsert_listing(
    conn: psycopg.Connection[Any],
    listing: ListingRow,
    stats: IngestStats,
) -> None:
    values = (
        listing.source,
        listing.external_id,
        listing.source_url,
        listing.url_canonical,
        listing.title_raw,
        listing.company,
        listing.role_family,
        listing.city,
        listing.city_raw,
        listing.seniority,
        listing.work_mode,
        listing.posted_at,
        listing.posted_at_raw,
        listing.description,
        listing.content_hash,
        listing.description_hash,
    )

    exists = conn.execute(
        "SELECT 1 FROM listings WHERE url_canonical = %s", (listing.url_canonical,)
    ).fetchone()

    if exists is None:
        conn.execute(_INSERT_LISTING, values)
        stats.inserted += 1
        return

    conn.execute(
        _UPDATE_LISTING,
        (
            listing.external_id,
            listing.source_url,
            listing.title_raw,
            listing.company,
            listing.role_family,
            listing.city,
            listing.city_raw,
            listing.seniority,
            listing.work_mode,
            listing.posted_at,
            listing.posted_at_raw,
            listing.description,
            listing.content_hash,
            listing.description_hash,
            listing.url_canonical,
        ),
    )
    stats.updated += 1
