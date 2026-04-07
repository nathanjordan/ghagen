"""Detect drift between committed schema snapshots and upstream."""

from __future__ import annotations

import difflib
import sys
import tempfile
from pathlib import Path

from ghagen.schema.codegen import generate_models
from ghagen.schema.fetch import SNAPSHOT_DIR, save_schema


def check_drift(snapshot_dir: Path | None = None) -> tuple[bool, str]:
    """Compare committed snapshots against freshly generated ones.

    Returns ``(has_drift, diff_output)`` where *has_drift* is ``True``
    when the upstream schema or generated models differ from the
    committed snapshots.
    """
    if snapshot_dir is None:
        snapshot_dir = SNAPSHOT_DIR

    diffs: list[str] = []

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)

        # Fetch fresh schema and generate fresh models
        fresh_schema = tmp_path / "workflow_schema.json"
        fresh_models = tmp_path / "_generated_models.py"
        save_schema(fresh_schema)
        generate_models(fresh_schema, fresh_models)

        # Compare each snapshot file
        for name in ("workflow_schema.json", "_generated_models.py"):
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
