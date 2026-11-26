-- Ingest bookkeeping added when the first adapter landed.
-- Idempotent on purpose: `make migrate` re-applies every file.

ALTER TABLE listings ADD COLUMN IF NOT EXISTS company TEXT;

ALTER TABLE ingest_runs ADD COLUMN IF NOT EXISTS updated INT DEFAULT 0;

COMMENT ON COLUMN listings.role_family IS
    'backend|frontend|fullstack|data|devops|security|qa|mobile|other';

CREATE INDEX IF NOT EXISTS listings_company_idx ON listings (lower(company));
