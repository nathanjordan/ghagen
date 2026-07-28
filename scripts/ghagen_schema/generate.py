"""``generate`` -- regenerate the TS reference types from the committed Snapshot.

Offline and a pure function of the committed Snapshot: it shells the TypeScript
codegen (``json-schema-to-typescript`` only exists in that toolchain), which
reads ``schema/*.json`` and writes ``packages/typescript/src/schema/*.generated.ts``
reformatted with ``oxfmt`` so regeneration is byte-stable under ``fmt.sh``.
"""

from __future__ import annotations

import subprocess

from .paths import REPO_ROOT

#: Directory of the TypeScript package whose codegen we shell into.
TS_PACKAGE_DIR = REPO_ROOT / "packages" / "typescript"


def run() -> int:
    """Execute the ``generate`` verb by shelling the TS codegen."""
    subprocess.run(
        ["npm", "--prefix", str(TS_PACKAGE_DIR), "run", "generate-types"],
        cwd=REPO_ROOT,
        check=True,
    )
    return 0
