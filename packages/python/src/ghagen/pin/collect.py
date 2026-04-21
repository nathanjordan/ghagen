"""Collect all pinnable ``uses:`` references from an App."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from ghagen.models.action import Action, CompositeRuns
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


def _collect_from_steps(steps: list[object], refs: set[str]) -> None:
    """Add pinnable ``uses:`` refs from a list of Step items to *refs*."""
    for step in steps:
        if not isinstance(step, Step):
            continue
        if step.uses and _is_pinnable(step.uses):
            refs.add(step.uses)


def collect_uses_refs(app: App) -> set[str]:
    """Walk all items in *app* and return pinnable ``uses:`` strings.

    Scans:
    - Workflow jobs (``Job.uses`` for reusable workflows, ``Step.uses``
      for action references)
    - Composite Action steps (``Step.uses`` inside :class:`CompositeRuns`)

    Skips:
    - Local path refs (``./…``)
    - Docker image refs (``docker://…``)
    - Refs already pinned to a 40-char SHA
    - Docker and Node action ``runs:`` sections (no pinnable refs live
      there — ``DockerRuns.image`` is a ``docker://`` ref and
      ``NodeRuns.main`` is a JS entrypoint path)
    """
    refs: set[str] = set()

    for item, _path in app._items:
        if isinstance(item, Workflow):
            for job in item.jobs.values():
                # Job.uses — reusable workflow calls
                uses = getattr(job, "uses", None)
                if isinstance(uses, str) and _is_pinnable(uses):
                    refs.add(uses)

                # Step.uses — action references
                _collect_from_steps(list(getattr(job, "steps", None) or []), refs)
        elif isinstance(item, Action) and isinstance(item.runs, CompositeRuns):
            _collect_from_steps(list(item.runs.steps), refs)

    return refs
