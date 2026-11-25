-- Silabus schema. Applied by `make migrate`, reset with `make reset-db`.

CREATE TABLE IF NOT EXISTS ingest_runs (
  id         BIGSERIAL PRIMARY KEY,
  source     TEXT NOT NULL,
  started_at TIMESTAMPTZ NOT NULL,
  finished_at TIMESTAMPTZ,
  fetched    INT DEFAULT 0,
  inserted   INT DEFAULT 0,
  duplicates INT DEFAULT 0,
  errors     INT DEFAULT 0
);

-- Immutable evidence of what a source said on a given day. PII is stripped
-- BEFORE insert (src/silabus/ingest/base.py::scrub_payload).
CREATE TABLE IF NOT EXISTS raw_listings (
  id            BIGSERIAL PRIMARY KEY,
  run_id        BIGINT REFERENCES ingest_runs(id) ON DELETE SET NULL,
  source        TEXT NOT NULL,
  source_url    TEXT NOT NULL,
  url_canonical TEXT NOT NULL,
  fetch_date    DATE NOT NULL,
  fetched_at    TIMESTAMPTZ NOT NULL,
  payload       JSONB NOT NULL,
  UNIQUE (source, url_canonical, fetch_date)
);

CREATE TABLE IF NOT EXISTS listings (
  id               BIGSERIAL PRIMARY KEY,
  source           TEXT NOT NULL,
  external_id      TEXT,
  source_url       TEXT NOT NULL,
  url_canonical    TEXT NOT NULL,
  title_raw        TEXT NOT NULL,
  role_family      TEXT,
  city             TEXT,
  city_raw         TEXT,
  seniority        TEXT,
  work_mode        TEXT DEFAULT 'unknown'
                   CHECK (work_mode IN ('onsite', 'hybrid', 'remote', 'unknown')),
  posted_at        DATE,
  posted_at_raw    TEXT,
  description      TEXT,             -- cleaned + scrubbed; never served by the API
  content_hash     TEXT NOT NULL,    -- exact-duplicate key
  description_hash TEXT,             -- LLM cache key
  dedup_cluster_id BIGINT,           -- canonical listings.id; singleton = own id
  created_at       TIMESTAMPTZ DEFAULT now(),
  UNIQUE (url_canonical),
  UNIQUE (source, external_id)
);

CREATE INDEX IF NOT EXISTS listings_role_city_idx ON listings (role_family, city);
CREATE INDEX IF NOT EXISTS listings_cluster_idx ON listings (dedup_cluster_id);
CREATE INDEX IF NOT EXISTS listings_posted_idx ON listings (posted_at);

CREATE TABLE IF NOT EXISTS skills (
  id        SERIAL PRIMARY KEY,
  canonical TEXT UNIQUE NOT NULL,
  aliases   TEXT[] NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS listing_skills (
  listing_id BIGINT REFERENCES listings(id) ON DELETE CASCADE,
  skill_id   INT REFERENCES skills(id) ON DELETE CASCADE,
  method     TEXT NOT NULL CHECK (method IN ('dictionary', 'llm', 'manual')),
  confidence REAL,
  PRIMARY KEY (listing_id, skill_id, method)
);

-- Ground truth for evaluation. Keyed by content_hash so that rebuilding the
-- listings table never orphans the labels.
CREATE TABLE IF NOT EXISTS skill_labels (
  content_hash     TEXT PRIMARY KEY,
  url_canonical    TEXT NOT NULL,
  role_family      TEXT,
  skills_gold      TEXT[] NOT NULL,
  labeler          TEXT NOT NULL,
  taxonomy_version TEXT NOT NULL,
  labeled_at       TIMESTAMPTZ DEFAULT now()
);

-- Changing the model or the prompt must never reuse an old answer.
CREATE TABLE IF NOT EXISTS extract_cache (
  description_hash TEXT NOT NULL,
  model            TEXT NOT NULL,
  prompt_version   TEXT NOT NULL,
  output           JSONB NOT NULL,
  input_tokens     INT,
  output_tokens    INT,
  cost_usd         NUMERIC(10, 6),
  created_at       TIMESTAMPTZ DEFAULT now(),
  PRIMARY KEY (description_hash, model, prompt_version)
);

-- One row per evaluation, so every number in the README is reproducible.
CREATE TABLE IF NOT EXISTS eval_runs (
  id               BIGSERIAL PRIMARY KEY,
  run_at           TIMESTAMPTZ DEFAULT now(),
  method           TEXT NOT NULL,
  model            TEXT,
  prompt_version   TEXT,
  taxonomy_version TEXT,
  git_sha          TEXT,
  n_docs           INT NOT NULL,
  precision        REAL,
  recall           REAL,
  f1               REAL,
  cost_usd         NUMERIC(10, 6)
);

-- One row per (listing, skill), with method precedence manual > dictionary > llm.
CREATE OR REPLACE VIEW v_resolved_skills AS
SELECT listing_id,
       skill_id,
       CASE
         WHEN bool_or(method = 'manual')     THEN 'manual'
         WHEN bool_or(method = 'dictionary') THEN 'dictionary'
         ELSE 'llm'
       END AS method
FROM listing_skills
GROUP BY listing_id, skill_id
HAVING bool_or(method IN ('manual', 'dictionary'))
    OR max(confidence) FILTER (WHERE method = 'llm') >= 0.7;

CREATE OR REPLACE VIEW mart_scope AS
SELECT role_family,
       city,
       work_mode,
       seniority,
       count(DISTINCT coalesce(dedup_cluster_id, id)) AS listings
FROM listings
GROUP BY 1, 2, 3, 4;

-- Demand counts CLUSTERS, not rows: the same job on two ATS vendors is one job.
CREATE OR REPLACE VIEW mart_skill_demand AS
SELECT l.role_family,
       l.city,
       s.canonical,
       count(DISTINCT coalesce(l.dedup_cluster_id, l.id)) AS listings
FROM listings l
JOIN v_resolved_skills rs ON rs.listing_id = l.id
JOIN skills s ON s.id = rs.skill_id
GROUP BY 1, 2, 3;
