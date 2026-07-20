"""Collect all pinnable ``uses:`` references from an App."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ghagen.models.job import Job
from ghagen.models.step import Step

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
    """Walk every registered item in *app* and return pinnable ``uses:`` strings.

    Traverses each Workflow/Action via :meth:`~ghagen.models._base.GhagenModel.walk`
    and collects pinnable refs from:

    - **Step** ``uses`` — action references (wherever a Step lives: workflow
      jobs or composite action ``runs.steps``)
    - **Job** ``uses`` — reusable workflow calls

    Skips local path refs (``./…``), docker image refs (``docker://…``), and
    refs already pinned to a 40-char SHA.
    """
    refs: set[str] = set()

    for item, _path in app._items:
        for _p, model in item.walk():
            # Only Step (action refs) and Job (reusable workflow calls) carry uses.
            uses = model.uses if isinstance(model, (Step, Job)) else None
            if isinstance(uses, str) and _is_pinnable(uses):
                refs.add(uses)

    return refs
