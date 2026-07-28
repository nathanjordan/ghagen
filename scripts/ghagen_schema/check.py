"""``check`` -- regenerate into place and assert the generated types are clean.

Offline, deterministic, CI-safe: ``generate`` + ``git diff --exit-code`` over
the generated types. This is the missing ADR-0003 guarantee -- "the committed
generated types match the committed Snapshot." It never fetches, so it adds no
network flake and needs no ``GITHUB_TOKEN``; safe to run on every PR.
"""

from __future__ import annotations

import subprocess

from . import generate
from .paths import REPO_ROOT

#: The generated TypeScript reference types guarded against staleness.
GENERATED_TYPES_DIR = REPO_ROOT / "packages" / "typescript" / "src" / "schema"


def run() -> int:
    """Execute the ``check`` verb: regenerate, then assert git-clean."""
    rc = generate.run()
    if rc != 0:
        return rc

    rel = GENERATED_TYPES_DIR.relative_to(REPO_ROOT)
    diff = subprocess.run(
        ["git", "diff", "--exit-code", "--", str(rel)],
        cwd=REPO_ROOT,
    )
    if diff.returncode != 0:
        print(
            "\nSchema types are stale: the committed generated types under "
            f"{rel} do not match the committed Snapshot in schema/. "
            "Run `uv run python -m ghagen_schema generate` and commit the result."
        )
        return 1

    print(f"Schema types are up to date ({rel} matches schema/).")
    return 0
