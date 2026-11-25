"""Command line entry point (`uv run silabus ...`).

Subcommands are declared up front so the Makefile targets stay stable. Each one
prints a message until it is actually wired up.
"""

from __future__ import annotations

import argparse
from collections.abc import Sequence

EXIT_NOT_IMPLEMENTED = 2


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="silabus", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    ingest = sub.add_parser("ingest", help="fetch listings into raw_listings")
    ingest.add_argument("--source", default="fixtures", help="fixtures|curated|greenhouse|lever")

    evaluate = sub.add_parser("eval", help="score extraction against frozen labels")
    evaluate.add_argument("--mode", choices=("smoke", "full"), default="smoke")

    sub.add_parser("taxonomy-sync", help="sync skills.yaml into the skills table")

    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    print(f"{args.command} is not implemented yet")
    return EXIT_NOT_IMPLEMENTED
