"""Dev-only schema sync + drift detection for the GitHub Actions JSON Schemas.

This is **maintainer tooling**, not a shipped runtime feature (see ADR-0003).
ghagen tracks two schemas from SchemaStore -- the workflow schema (for
``.github/workflows/*.yml``) and the action schema (for ``action.yml``) -- as a
single canonical snapshot at the repo root under ``schema/``. That snapshot is
consumed by both test suites, the TypeScript codegen, and drift detection.

Drift detection here is a pure JSON comparison: fetch the upstream schemas and
diff them against the committed canonical snapshot. No Python models are
generated (the hand-written Pydantic models are the public API; the schema is a
conformance target -- see ADR-0003).

Usage::

    uv run python packages/python/scripts/schema_sync.py sync         # overwrite
    uv run python packages/python/scripts/schema_sync.py check-drift   # exit 1 on drift
"""

from __future__ import annotations

import argparse
import difflib
import json
import sys
import tempfile
from pathlib import Path
from typing import Any

import httpx

#: Repo root: schema_sync.py lives at ``<root>/packages/python/scripts/``.
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Canonical schema snapshot directory (single source of truth).
SCHEMA_DIR = REPO_ROOT / "schema"

#: Registry of known schemas. Keyed by short name.
SCHEMAS: dict[str, dict[str, str]] = {
    "workflow": {
        "url": "https://json.schemastore.org/github-workflow.json",
        "filename": "workflow_schema.json",
    },
    "action": {
        "url": "https://json.schemastore.org/github-action.json",
        "filename": "action_schema.json",
    },
}


def fetch_schema(name: str = "workflow") -> dict[str, Any]:
    """Download a schema from SchemaStore.

    Args:
        name: Short name of the schema (see :data:`SCHEMAS`).

    Returns:
        The parsed JSON Schema as a dict.
    """
    url = SCHEMAS[name]["url"]
    resp = httpx.get(url, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _serialize(schema: dict[str, Any]) -> str:
    """Render a schema as deterministic, pretty-printed JSON.

    Keys are sorted so committed snapshots are reproducible regardless of the
    upstream key order.
    """
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def save_schema(dest: Path, name: str = "workflow") -> None:
    """Fetch *name* and write it to *dest* as deterministic JSON."""
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_serialize(fetch_schema(name)))


def save_all_schemas(schema_dir: Path | None = None) -> list[Path]:
    """Fetch and write every known schema to *schema_dir*.

    Returns the list of written paths, in registry order.
    """
    target = schema_dir if schema_dir is not None else SCHEMA_DIR
    written: list[Path] = []
    for name, info in SCHEMAS.items():
        dest = target / info["filename"]
        save_schema(dest, name)
        written.append(dest)
    return written


def check_drift(schema_dir: Path | None = None) -> tuple[bool, str]:
    """Compare the committed canonical snapshot against upstream.

    Fetches every registered schema fresh and diffs it against the committed
    JSON. No models are generated -- drift is a pure JSON comparison.

    Returns ``(has_drift, diff_output)`` where *has_drift* is ``True`` when any
    upstream schema differs from the committed snapshot.
    """
    if schema_dir is None:
        schema_dir = SCHEMA_DIR

    diffs: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        save_all_schemas(tmp_path)

        for info in SCHEMAS.values():
            filename = info["filename"]
            snapshot_file = schema_dir / filename
            fresh_file = tmp_path / filename

            if not snapshot_file.exists():
                diffs.append(f"Missing snapshot: {snapshot_file}\n")
                continue

            committed = snapshot_file.read_text()
            upstream = fresh_file.read_text()
            if committed != upstream:
                diff = difflib.unified_diff(
                    committed.splitlines(keepends=True),
                    upstream.splitlines(keepends=True),
                    fromfile=f"{filename} (committed)",
                    tofile=f"{filename} (upstream)",
                )
                diffs.append("".join(diff))

    return (bool(diffs), "\n".join(diffs))


def _cmd_sync() -> int:
    for dest in save_all_schemas():
        print(f"Saved schema to {dest}")
    return 0


def _cmd_check_drift() -> int:
    has_drift, diff_output = check_drift()
    if has_drift:
        print("Schema drift detected:\n")
        print(diff_output)
        return 1
    print("No schema drift detected.")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "sync",
        help="Fetch upstream schemas and overwrite the canonical snapshot.",
    )
    sub.add_parser(
        "check-drift",
        help="Fetch upstream and diff against the snapshot; exit 1 on drift.",
    )
    args = parser.parse_args(argv)

    if args.command == "sync":
        return _cmd_sync()
    return _cmd_check_drift()


if __name__ == "__main__":
    sys.exit(main())
