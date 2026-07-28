"""``sync`` -- fetch upstream schemas and overwrite the canonical Snapshot.

The only verb that touches the network. Serialization is deterministic
(sorted keys, trailing newline) so committed Snapshots are reproducible
regardless of upstream key order.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

from .manifest import ManifestEntry, load_manifest
from .paths import SCHEMA_DIR


def fetch_schema(entry: ManifestEntry) -> dict[str, Any]:
    """Download the schema for *entry* from SchemaStore."""
    resp = httpx.get(entry.url, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def _serialize(schema: dict[str, Any]) -> str:
    """Render a schema as deterministic, pretty-printed JSON.

    Keys are sorted so committed Snapshots are reproducible regardless of the
    upstream key order.
    """
    return json.dumps(schema, indent=2, sort_keys=True) + "\n"


def save_schema(entry: ManifestEntry, schema_dir: Path) -> Path:
    """Fetch *entry* and write it into *schema_dir* as deterministic JSON."""
    dest = schema_dir / entry.filename
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(_serialize(fetch_schema(entry)))
    return dest


def save_all_schemas(schema_dir: Path | None = None) -> list[Path]:
    """Fetch and write every manifest schema to *schema_dir*, in registry order."""
    target = schema_dir if schema_dir is not None else SCHEMA_DIR
    return [save_schema(entry, target) for entry in load_manifest()]


def run() -> int:
    """Execute the ``sync`` verb."""
    for dest in save_all_schemas():
        print(f"Saved schema to {dest}")
    return 0
