# Silabus

[![ci](https://github.com/philipphqiwu/silabus/actions/workflows/ci.yml/badge.svg)](https://github.com/philipphqiwu/silabus/actions/workflows/ci.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)

Silabus reads tech job postings in Indonesia and counts which skills actually show up, per role and per city.

The part I care about is the gap check: send it the skills you already have and it returns what you are missing for a target role, sorted by how often those skills appear in real postings. The rest of the pipeline exists so that number is worth trusting.

**Status:** early. Ingest works for Greenhouse, live or from recorded fixtures, and it is idempotent: running it twice does not add rows. Dedup, skill extraction, `/gap` and the dashboard are still missing, so there are no market numbers yet.

## Running it

Needs Docker and [uv](https://docs.astral.sh/uv/).

```bash
cp .env.example .env
make up        # Postgres 16 on 5433
make migrate   # schema
make ingest    # loads data/fixtures into listings
make test
make api       # http://localhost:8000/health
```

The fixture is a recording of the Greenhouse board payload shape, with fictional companies. To pull a real board: `make ingest SOURCE=greenhouse BOARD=<slug>`.

`make help` lists the rest.

## Layout

```
src/silabus/ingest      adapters, PII scrubbing, idempotent writes
src/silabus/normalize   urls, titles, cities, seniority, description cleanup
src/silabus/dedup       exact hash first, then MinHash for cross-board duplicates
src/silabus/extract     skill dictionary, plus an LLM pass for what it misses
src/silabus/api         /health today, /gap once there is data
db/migrations           schema
```

## Data

Postings come from public ATS job boards: Greenhouse, Lever, Workable, Ashby. One adapter per vendor, no HTML scraping for now.

JobStreet, Glints, Kalibrr and LinkedIn are out. Their terms do not allow automated collection and I did not want to build the project around that.

Recruiter emails and phone numbers are dropped before anything is written to disk. Descriptions are used to pull out skills and never returned by the API.

More in [docs/data-sources.md](docs/data-sources.md).

## Caveats

The sample will lean toward companies that use a modern ATS and toward jobs in the big cities. It is not a census of the Indonesian job market and I will not describe it as one.

## License

MIT, see [LICENSE](LICENSE).
