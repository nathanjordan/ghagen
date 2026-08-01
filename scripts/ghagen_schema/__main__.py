"""Argparse dispatch for the three-verb schema pipeline.

python -m ghagen_schema sync       # network: refresh the Snapshot
python -m ghagen_schema generate   # offline: regenerate the TS types
python -m ghagen_schema check      # offline: staleness guard (CI-safe)
"""

from __future__ import annotations

import argparse
import sys

from . import check, generate, sync


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="ghagen_schema", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "sync",
        help="Network: fetch upstream schemas and overwrite the Snapshot.",
    )
    sub.add_parser(
        "generate",
        help="Offline: regenerate the TS reference types from the Snapshot.",
    )
    sub.add_parser(
        "check",
        help="Offline: regenerate and assert the generated types are not stale.",
    )
    args = parser.parse_args(argv)

    return {
        "sync": sync.run,
        "generate": generate.run,
        "check": check.run,
    }[args.command]()


if __name__ == "__main__":
    sys.exit(main())
