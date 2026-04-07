"""Fetch the GitHub Actions workflow JSON Schema from SchemaStore."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import httpx

SCHEMASTORE_URL = "https://json.schemastore.org/github-workflow.json"
SNAPSHOT_DIR = Path(__file__).parent / "snapshot"


def fetch_schema() -> dict[str, Any]:
    """Download the latest workflow JSON Schema from SchemaStore."""
    resp = httpx.get(SCHEMASTORE_URL, follow_redirects=True)
    resp.raise_for_status()
    return resp.json()  # type: ignore[no-any-return]


def save_schema(dest: Path) -> None:
    """Fetch the schema and write it to *dest* as pretty-printed JSON."""
    schema = fetch_schema()
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(schema, indent=2, sort_keys=True) + "\n")


if __name__ == "__main__":
    out = SNAPSHOT_DIR / "workflow_schema.json"
    save_schema(out)
    print(f"Saved schema to {out}")
