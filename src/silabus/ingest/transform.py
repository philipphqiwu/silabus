"""From a source posting to the columns of `listings`."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from silabus.ingest.base import SourceJob
from silabus.normalize.cities import parse_location
from silabus.normalize.dates import parse_posted_at
from silabus.normalize.description import clean_description
from silabus.normalize.hashing import content_hash, description_hash
from silabus.normalize.seniority import seniority as parse_seniority
from silabus.normalize.titles import role_family
from silabus.normalize.urls import canonicalize_url


@dataclass(frozen=True, slots=True)
class ListingRow:
    source: str
    external_id: str
    source_url: str
    url_canonical: str
    title_raw: str
    company: str | None
    role_family: str
    city: str | None
    city_raw: str | None
    seniority: str
    work_mode: str
    posted_at: date | None
    posted_at_raw: str | None
    description: str
    content_hash: str
    description_hash: str


def to_listing_row(job: SourceJob) -> ListingRow:
    """Normalize one posting. Raises ValueError on an unusable URL."""
    description = clean_description(job.description_html)
    city, work_mode = parse_location(job.location)

    return ListingRow(
        source=job.source,
        external_id=job.external_id,
        source_url=job.source_url,
        url_canonical=canonicalize_url(job.source_url),
        title_raw=job.title,
        company=job.company,
        role_family=role_family(job.title),
        city=city,
        city_raw=job.location,
        seniority=parse_seniority(job.title),
        work_mode=work_mode,
        posted_at=parse_posted_at(job.posted_at_raw),
        posted_at_raw=job.posted_at_raw,
        description=description,
        content_hash=content_hash(
            title=job.title,
            company=job.company,
            city=city,
            description=description,
        ),
        description_hash=description_hash(description),
    )
