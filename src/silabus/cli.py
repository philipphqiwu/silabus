"""Command line entry point (`uv run silabus ...`).

Subcommands are declared up front so the Makefile targets stay stable. Each one
prints a message until it is actually wired up.
"""

from __future__ import annotations

import argparse
import sys
from collections.abc import Sequence
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from silabus.ingest.runner import IngestStats

EXIT_OK = 0
EXIT_FAILED = 1
EXIT_NOT_IMPLEMENTED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="silabus", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="fetch postings into raw_listings and listings")
    ingest.add_argument("--source", default="fixtures", help="fixtures, greenhouse or workable")
    ingest.add_argument("--board", default=None, help="ATS board slug, e.g. acme")
    ingest.add_argument(
        "--fixture-dir",
        default="data/fixtures",
        help="directory with recorded payloads (source=fixtures)",
    )

    evaluate = sub.add_parser("eval", help="score extraction against frozen labels")
    evaluate.add_argument("--mode", choices=("smoke", "full"), default="smoke")

    sub.add_parser("migrate", help="apply pending db/migrations")

    sub.add_parser("taxonomy-sync", help="sync skills.yaml into the skills table")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    if args.command == "ingest":
        return _cmd_ingest(args)

    if args.command == "migrate":
        return _cmd_migrate()

    print(f"{args.command} is not implemented yet")
    return EXIT_NOT_IMPLEMENTED


def _cmd_ingest(args: argparse.Namespace) -> int:
    from silabus.ingest.runner import run_ingest
    from silabus.ingest.sources import load_jobs

    try:
        jobs = load_jobs(
            args.source,
            board=args.board,
            fixture_dir=Path(args.fixture_dir),
        )
    except ValueError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_FAILED

    stats: IngestStats = run_ingest(jobs, source_name=args.source)
    print(
        f"{stats.source}: fetched={stats.fetched} inserted={stats.inserted} "
        f"updated={stats.updated} duplicates={stats.duplicates} errors={stats.errors}"
    )
    return EXIT_OK if stats.errors == 0 else EXIT_FAILED


def _cmd_migrate() -> int:
    from silabus.migrate import apply_migrations

    applied = apply_migrations()
    if not applied:
        print("schema is up to date")
    for name in applied:
        print(f"applied {name}")
    return EXIT_OK
