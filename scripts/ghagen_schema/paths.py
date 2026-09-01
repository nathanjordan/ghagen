"""The one Python repo-root / test-path resolver.

Replaces the ~4 duplicated Python resolutions (the brittle ``parents[N]``
hardcode in the conformance sweep and the two walk-up copies in the integration
and deps test suites) with a single walk-up that *asserts* it found the root,
so no move of a caller can silently retarget it.
"""

from __future__ import annotations

from pathlib import Path


def repo_root() -> Path:
    """Return the repo root: the ancestor directory containing ``schema/``.

    Raises:
        RuntimeError: if no ancestor contains a ``schema/`` directory.
    """
    d = Path(__file__).resolve().parent
    while d != d.parent:
        if (d / "schema").is_dir():
            return d
        d = d.parent
    raise RuntimeError("Cannot find repo root (directory containing schema/)")


#: Repo root (single source of truth for path resolution).
REPO_ROOT = repo_root()

#: Canonical schema Snapshot directory (single source of truth).
SCHEMA_DIR = REPO_ROOT / "schema"

#: The fixtures directory (holds ``expected/`` plus other fixture data such as
#: ``cli-exit-codes.yml`` and ``cli-exit-code-projects/``).
FIXTURES_ROOT = REPO_ROOT / "fixtures"

#: Shared golden fixtures consumed by both ports' test suites.
EXPECTED_DIR = FIXTURES_ROOT / "expected"
