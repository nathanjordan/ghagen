"""``check`` -- assert the generated types are clean, without changing the tree.

Offline, deterministic, CI-safe: ``generate`` + ``git diff --exit-code`` over
the generated types. This is the missing ADR-0003 guarantee -- "the committed
generated types match the committed Snapshot." It never fetches, so it adds no
network flake and needs no ``GITHUB_TOKEN``; safe to run on every PR.

``generate`` writes into the tree, so ``check`` snapshots the generated
directory, regenerates, diffs, and restores -- on both the pass and the fail
path. That makes it read-only, which is what lets it run from a local gate
(``scripts/lint.sh meta``) and a pre-commit hook without rewriting tracked
files behind the author's back.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from . import generate
from .paths import REPO_ROOT

#: The generated TypeScript reference types guarded against staleness.
#: Also the complete write set of ``generate``, hence the complete snapshot set.
GENERATED_TYPES_DIR = REPO_ROOT / "packages" / "typescript" / "src" / "schema"


def run() -> int:
    """Execute the ``check`` verb: regenerate, assert git-clean, restore the tree."""
    rel = GENERATED_TYPES_DIR.relative_to(REPO_ROOT)

    with tempfile.TemporaryDirectory() as tmp:
        backup = Path(tmp) / "schema"
        shutil.copytree(GENERATED_TYPES_DIR, backup)
        try:
            rc = generate.run()
            if rc != 0:
                return rc

            diff = subprocess.run(
                ["git", "diff", "--exit-code", "--", str(rel)],
                cwd=REPO_ROOT,
            )
        finally:
            shutil.rmtree(GENERATED_TYPES_DIR)
            shutil.copytree(backup, GENERATED_TYPES_DIR)

    if diff.returncode != 0:
        print(
            "\nSchema types are stale: the committed generated types under "
            f"{rel} do not match the committed Snapshot in schema/. "
            "Run `uv run python -m ghagen_schema generate` and commit the result."
        )
        return 1

    print(f"Schema types are up to date ({rel} matches schema/).")
    return 0
