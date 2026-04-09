"""Collect all pinnable ``uses:`` references from an App."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ghagen.models.step import Step
from ghagen.models.workflow import Workflow

if TYPE_CHECKING:
    from ghagen.app import App

# 40-character lowercase hex — already a commit SHA.
_SHA_RE = re.compile(r"^[0-9a-f]{40}$")


def _is_pinnable(uses: str) -> bool:
    """Return True if ``uses`` is a remote action/workflow ref that can be pinned."""
    # Skip local paths and docker images.
    if uses.startswith("./") or uses.startswith("docker://"):
        return False

    # Must have an @ref component.
    if "@" not in uses:
        return False

    # Already pinned to a SHA — nothing to do.
    _, ref = uses.rsplit("@", 1)
    return not _SHA_RE.match(ref)


def collect_uses_refs(app: App) -> set[str]:
    """Walk all Workflow items in *app* and return pinnable ``uses:`` strings.

    Skips:
    - Local path refs (``./…``)
    - Docker image refs (``docker://…``)
    - Refs already pinned to a 40-char SHA
    - Action items (only workflows are scanned)
    """
    refs: set[str] = set()

    for item, _path in app._items:
        if not isinstance(item, Workflow):
            continue

        for job in item.jobs.values():
            # Job.uses — reusable workflow calls
            uses = getattr(job, "uses", None)
            if isinstance(uses, str) and _is_pinnable(uses):
                refs.add(uses)

            # Step.uses — action references
            steps = getattr(job, "steps", None) or []
            for step in steps:
                if not isinstance(step, Step):
                    continue
                if step.uses and _is_pinnable(step.uses):
                    refs.add(step.uses)

    return refs
