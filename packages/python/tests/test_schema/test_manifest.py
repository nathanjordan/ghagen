"""Tests for the validated manifest interface (``ghagen_schema.manifest``).

The manifest is the sole owner of the ``<name>_schema.json ->
<name>-types.generated.ts`` filename convention. These tests pin the derivation
and, crucially, that a convention violation fails *loudly* -- the enforcement
the old silent-no-op regex in ``generate-types.ts`` never had.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from ghagen_schema.manifest import (
    ManifestEntry,
    derive_generated_filename,
    load_manifest,
)


def test_derive_generated_filename() -> None:
    assert derive_generated_filename("workflow_schema.json") == (
        "workflow-types.generated.ts"
    )
    assert derive_generated_filename("action_schema.json") == (
        "action-types.generated.ts"
    )


def test_derive_generated_filename_rejects_bad_suffix() -> None:
    with pytest.raises(ValueError, match="_schema.json"):
        derive_generated_filename("workflow.json")


def test_entry_generated_filename() -> None:
    entry = ManifestEntry(
        name="workflow", url="http://x", filename="workflow_schema.json"
    )
    assert entry.generated_filename == "workflow-types.generated.ts"


def test_load_manifest_returns_typed_entries() -> None:
    entries = load_manifest()
    assert {e.name for e in entries} == {"workflow", "action"}
    for entry in entries:
        assert entry.generated_filename.endswith("-types.generated.ts")


def test_load_manifest_raises_on_convention_violation(tmp_path: Path) -> None:
    """A filename not ending in ``_schema.json`` fails loudly at load."""
    bad = tmp_path / "manifest.json"
    bad.write_text(
        json.dumps({"workflow": {"url": "http://x", "filename": "workflow.json"}})
    )
    with pytest.raises(ValueError, match="workflow.json"):
        load_manifest(bad)


def test_load_manifest_raises_on_malformed_entry(tmp_path: Path) -> None:
    bad = tmp_path / "manifest.json"
    bad.write_text(json.dumps({"workflow": {"url": "http://x"}}))
    with pytest.raises(ValueError, match="'url' and"):
        load_manifest(bad)
