"""Make the dev-only ``schema_sync`` tooling importable in schema tests.

The schema sync + drift tooling lives under ``packages/python/scripts/`` (it is
maintainer tooling, not part of the shipped ``ghagen`` package -- see ADR-0003),
so it is not on the import path by default. Insert the scripts directory so the
tests can import it directly.
"""

from __future__ import annotations

import sys
from pathlib import Path

_SCRIPTS_DIR = Path(__file__).resolve().parents[2] / "scripts"
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))
