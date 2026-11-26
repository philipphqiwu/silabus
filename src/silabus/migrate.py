"""Apply db/migrations in filename order, once each.

Kept in Python rather than a shell loop so contributors do not need psql
installed, and so CI and local runs use the same code path.
"""

from __future__ import annotations

from pathlib import Path

from silabus.db import connect

MIGRATIONS_DIR = Path("db/migrations")


def apply_migrations(directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply pending migrations and return the names that ran."""
    files = sorted(directory.glob("*.sql"))
    if not files:
        raise FileNotFoundError(f"no migrations in {directory}")

    applied: list[str] = []
    with connect() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                name       TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        done = {
            str(row[0]) for row in conn.execute("SELECT name FROM schema_migrations").fetchall()
        }

        for path in files:
            if path.name in done:
                continue
            conn.execute(path.read_text())
            conn.execute("INSERT INTO schema_migrations (name) VALUES (%s)", (path.name,))
            applied.append(path.name)

    return applied
