"""Postgres access.

psycopg directly, no ORM. The schema in db/migrations is the source of truth.
"""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from typing import Any

import psycopg
from psycopg import Connection

from silabus.config import get_settings

Row = tuple[Any, ...]


@contextmanager
def connect() -> Iterator[Connection[Row]]:
    """Open a connection, commit on clean exit, roll back on exception."""
    with psycopg.connect(get_settings().database_url) as conn:
        yield conn
