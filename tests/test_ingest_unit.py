from __future__ import annotations

import json
from pathlib import Path

import pytest

from silabus.ingest.ats_greenhouse import parse_board
from silabus.ingest.base import scrub_payload
from silabus.ingest.transform import to_listing_row
from silabus.normalize.cities import parse_location
from silabus.normalize.dates import parse_posted_at
from silabus.normalize.description import clean_description
from silabus.normalize.hashing import content_hash
from silabus.normalize.seniority import seniority
from silabus.normalize.titles import role_family

FIXTURE = Path("data/fixtures/greenhouse_acmenusantara.json")


def test_scrub_payload_drops_contact_fields_and_redacts_text() -> None:
    payload = {
        "id": 1,
        "company_name": "Acme",
        "contact_email": "hr@acme.example",
        "recruiter_name": "Someone Real",
        "location": {"name": "Jakarta"},
        "description": "Kirim CV ke talent@acme.example atau +62 812-3456-7890",
        "notes": ["email: a@b.co"],
    }

    cleaned = scrub_payload(payload)

    assert "contact_email" not in cleaned
    assert "recruiter_name" not in cleaned
    assert cleaned["company_name"] == "Acme"
    assert cleaned["location"] == {"name": "Jakarta"}
    assert "talent@acme.example" not in cleaned["description"]
    assert "812-3456-7890" not in cleaned["description"]
    assert "a@b.co" not in cleaned["notes"][0]


def test_scrub_payload_does_not_mutate_the_input() -> None:
    payload = {"contact_email": "hr@acme.example", "title": "Engineer"}
    scrub_payload(payload)
    assert payload["contact_email"] == "hr@acme.example"


def test_clean_description_handles_double_escaped_html() -> None:
    raw = "&lt;p&gt;Go and &lt;b&gt;PostgreSQL&lt;/b&gt;&lt;/p&gt;&lt;p&gt;Kafka&lt;/p&gt;"
    text = clean_description(raw)
    assert text == "Go and PostgreSQL\nKafka"


def test_clean_description_removes_scripts_and_collapses_whitespace() -> None:
    raw = "<script>alert(1)</script><p>Backend   engineer</p><div>Docker</div>"
    text = clean_description(raw)
    assert "alert" not in text
    assert "Backend engineer" in text
    assert text.splitlines() == ["Backend engineer", "Docker"]


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Jakarta Selatan, Indonesia", ("Jakarta", "onsite")),
        ("DKI Jakarta", ("Jakarta", "onsite")),
        ("Remote - Indonesia", (None, "remote")),
        ("Bandung, Indonesia", ("Bandung", "onsite")),
        ("Hybrid - Jakarta", ("Jakarta", "hybrid")),
        ("Bangkok, Thailand; Jakarta, Indonesia; Kuala Lumpur, Malaysia", ("Jakarta", "onsite")),
        ("Hong Kong; Shanghai, China; Taipei, Taiwan", ("Hong Kong", "onsite")),
        ("India; Jakarta, Indonesia", ("Jakarta", "onsite")),
        ("Location: Jakarta, Indonesia", ("Jakarta", "onsite")),
        ("Jakarta or Bandung", ("Jakarta", "onsite")),
        ("South Jakarta, Indonesia", ("Jakarta", "onsite")),
        ("West Jakarta", ("Jakarta", "onsite")),
        ("", (None, "unknown")),
    ],
)
def test_parse_location(raw: str, expected: tuple[str | None, str]) -> None:
    assert parse_location(raw) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Backend Engineer (Go)", "backend"),
        ("Senior Frontend Engineer (React)", "frontend"),
        ("React Native Developer", "mobile"),
        ("Data Engineer", "data"),
        ("Site Reliability Engineer", "devops"),
        ("QA Automation Engineer", "qa"),
        ("Full Stack Developer", "fullstack"),
        ("Security Analyst", "security"),
        ("Product Designer", "other"),
    ],
)
def test_role_family(title: str, expected: str) -> None:
    assert role_family(title) == expected


@pytest.mark.parametrize(
    ("title", "expected"),
    [
        ("Senior Backend Engineer", "senior"),
        ("Staff Engineer", "lead"),
        ("Junior Developer", "junior"),
        ("Backend Engineering Intern", "intern"),
        ("Backend Engineer", "unknown"),
    ],
)
def test_seniority(title: str, expected: str) -> None:
    assert seniority(title) == expected


def test_parse_posted_at_rejects_prose_dates() -> None:
    parsed = parse_posted_at("2026-11-02T03:00:00-05:00")
    assert parsed is not None
    assert parsed.isoformat() == "2026-11-02"
    assert parse_posted_at("3 days ago") is None
    assert parse_posted_at(None) is None


def test_parse_board_reads_every_field_the_pipeline_needs() -> None:
    payload = json.loads(FIXTURE.read_text())
    jobs = parse_board(payload, board="acmenusantara")

    assert len(jobs) == 5
    first = jobs[0]
    assert first.source == "greenhouse"
    assert first.external_id == "9001"
    assert first.company == "Acme Nusantara"
    assert first.location == "Jakarta Selatan, Indonesia"
    assert first.posted_at_raw == "2026-11-02T03:00:00-05:00"
    assert first.description_html is not None
    assert first.description_html.startswith("&lt;p&gt;")


def test_transform_normalizes_the_first_fixture_job() -> None:
    payload = json.loads(FIXTURE.read_text())
    row = to_listing_row(parse_board(payload, board="acmenusantara")[0])

    assert row.role_family == "backend"
    assert row.city == "Jakarta"
    assert row.city_raw == "Jakarta Selatan, Indonesia"
    assert row.work_mode == "onsite"
    assert row.posted_at is not None
    assert row.posted_at.isoformat() == "2026-11-02"
    assert "<p>" not in row.description
    assert row.url_canonical == "https://boards.greenhouse.io/acmenusantara/jobs/9001"


def test_content_hash_ignores_source_but_not_content() -> None:
    base = {"title": "Backend Engineer", "company": "Acme", "city": "Jakarta"}
    first = content_hash(description="Go and PostgreSQL", **base)
    second = content_hash(description="Go  and   PostgreSQL ", **base)
    other_city = content_hash(description="Go and PostgreSQL", **{**base, "city": "Bandung"})

    assert first == second
    assert first != other_city


WORKABLE_PAYLOAD = {
    "name": "Amartha",
    "jobs": [
        {
            "shortcode": "ABC123",
            "title": "Senior Backend Engineer",
            "url": "https://apply.workable.com/j/ABC123",
            "description": "<p>Go and PostgreSQL. Email jobs@amartha.example</p>",
            "requirements": "<ul><li>Docker</li><li>Kafka</li></ul>",
            "published_on": "2026-11-02",
            "telecommuting": False,
            "locations": [
                {
                    "city": "jakarta selatan",
                    "region": "DKI Jakarta",
                    "country": "Indonesia",
                }
            ],
        },
        {
            "shortcode": "REMOTE1",
            "title": "Data Engineer",
            "url": "https://apply.workable.com/j/REMOTE1",
            "description": "<p>Airflow and dbt</p>",
            "published_on": "2026-11-03",
            "telecommuting": True,
            "locations": [{"city": "bandung", "region": "West Java", "country": "Indonesia"}],
        },
    ],
}


def test_workable_parser_merges_requirements_into_the_description() -> None:
    from silabus.ingest.ats_workable import parse_account

    jobs = parse_account(WORKABLE_PAYLOAD, account="amartha")

    assert len(jobs) == 2
    first = jobs[0]
    assert first.source == "workable"
    assert first.external_id == "ABC123"
    assert first.company == "Amartha"
    assert first.location == "jakarta selatan, DKI Jakarta, Indonesia"
    assert first.posted_at_raw == "2026-11-02"
    assert "Docker" in str(first.description_html)
    assert "Kafka" in str(first.description_html)


def test_workable_posting_is_normalized_and_redacted() -> None:
    from silabus.ingest.ats_workable import parse_account

    jobs = parse_account(WORKABLE_PAYLOAD, account="amartha")
    first = to_listing_row(jobs[0])
    second = to_listing_row(jobs[1])

    assert first.role_family == "backend"
    assert first.seniority == "senior"
    assert first.city == "Jakarta"
    assert "jobs@amartha.example" not in first.description
    assert "Docker" in first.description

    assert second.work_mode == "remote"
    assert second.role_family == "data"
