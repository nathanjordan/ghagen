"""Fetch GitHub Actions JSON Schemas from SchemaStore.

ghagen tracks two schemas: the workflow schema (for ``.github/workflows/*.yml``)
and the action schema (for ``action.yml``). Both are cached under
:data:`SNAPSHOT_DIR` so tests can validate generated YAML without network
access and so drift can be detected in CI.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

SNAPSHOT_DIR = Path(__file__).parent / "snapshot"

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


def save_schema(dest: Path, name: str = "workflow") -> None:
    """Fetch *name* and write it to *dest* as pretty-printed JSON.

    Keys are sorted for reproducibility so committed snapshots are
    deterministic.
    """
    schema = fetch_schema(name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


def save_all_schemas(snapshot_dir: Path | None = None) -> list[Path]:
    """Fetch and write every known schema to *snapshot_dir*.

    Returns the list of written paths, in registry order.
    """
    target = snapshot_dir if snapshot_dir is not None else SNAPSHOT_DIR
    written: list[Path] = []
    for name, info in SCHEMAS.items():
        dest = target / info["filename"]
        save_schema(dest, name)
        written.append(dest)
    return written


if __name__ == "__main__":
    for dest in save_all_schemas():
        print(f"Saved schema to {dest}")
