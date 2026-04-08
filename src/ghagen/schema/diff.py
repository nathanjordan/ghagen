"""Detect drift between committed schema snapshots and upstream.

Compares both schemas (workflow + action) and both generated model
files against freshly fetched/generated versions. Used by CI to flag
upstream schema changes so ghagen can stay in sync.
"""

from __future__ import annotations

import difflib
import sys
import tempfile
from pathlib import Path

from ghagen.schema.codegen import _generated_filename, generate_all_models
from ghagen.schema.fetch import SCHEMAS, SNAPSHOT_DIR, save_all_schemas


def _tracked_files() -> list[str]:
    """Return the names of every snapshot file tracked for drift."""
    names: list[str] = []
    for name, info in SCHEMAS.items():
        names.append(info["filename"])
        names.append(_generated_filename(name))
    return names


def check_drift(snapshot_dir: Path | None = None) -> tuple[bool, str]:
    """Compare committed snapshots against freshly generated ones.

    Returns ``(has_drift, diff_output)`` where *has_drift* is ``True``
    when any upstream schema or generated models file differs from the
    committed snapshots.
    """
    if snapshot_dir is None:
        snapshot_dir = SNAPSHOT_DIR

    diffs: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Fetch fresh schemas and generate fresh models
        save_all_schemas(tmp_path)
        generate_all_models(tmp_path)

        for name in _tracked_files():
            snapshot_file = snapshot_dir / name
            fresh_file = tmp_path / name

            if not snapshot_file.exists():
                diffs.append(f"Missing snapshot: {snapshot_file}\n")
                continue

            actual = snapshot_file.read_text()
            expected = fresh_file.read_text()
            if actual != expected:
                diff = difflib.unified_diff(
                    actual.splitlines(keepends=True),
                    expected.splitlines(keepends=True),
                    fromfile=f"{name} (committed)",
                    tofile=f"{name} (upstream)",
                )
                diffs.append("".join(diff))

    combined = "\n".join(diffs)
    return (bool(diffs), combined)


if __name__ == "__main__":
    has_drift, diff_output = check_drift()
    if has_drift:
        print("Schema drift detected:\n")
        print(diff_output)
        sys.exit(1)
    else:
        print("No schema drift detected.")
