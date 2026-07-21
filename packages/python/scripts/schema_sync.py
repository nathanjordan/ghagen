"""Dev-only schema sync + drift detection for the GitHub Actions JSON Schemas.

This is **maintainer tooling**, not a shipped runtime feature (see ADR-0003).
ghagen tracks two schemas from SchemaStore -- the workflow schema (for
``.github/workflows/*.yml``) and the action schema (for ``action.yml``) -- as a
single canonical snapshot at the repo root under ``schema/``. That snapshot is
consumed by both test suites, the TypeScript codegen, and drift detection.

No Python models are generated (the hand-written Pydantic models are the public
API; the schema is a conformance target -- see ADR-0003). Drift is detected in
CI by running ``sync`` and diffing the snapshot with ``git`` (see
``.github/workflows/schema-drift.yml``), so no bespoke diff helper lives here.

Usage::

    uv run python packages/python/scripts/schema_sync.py sync         # overwrite
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import httpx

#: Repo root: schema_sync.py lives at ``<root>/packages/python/scripts/``.
REPO_ROOT = Path(__file__).resolve().parents[3]

#: Canonical schema snapshot directory (single source of truth).
SCHEMA_DIR = REPO_ROOT / "schema"

#: Shared schema registry: name -> {url, filename}. Read by this tool and by
#: ``packages/typescript/scripts/generate-types.ts``; adding a schema is a
#: single edit there.
MANIFEST_PATH = SCHEMA_DIR / "manifest.json"

#: Registry of known schemas, keyed by short name (loaded from the manifest).
SCHEMAS: dict[str, dict[str, str]] = json.loads(MANIFEST_PATH.read_text())


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


def _cmd_sync() -> int:
    for dest in save_all_schemas():
        print(f"Saved schema to {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    sub.add_parser(
        "sync",
        help="Fetch upstream schemas and overwrite the canonical snapshot.",
    )
    parser.parse_args(argv)
    return _cmd_sync()


if __name__ == "__main__":
    sys.exit(main())
