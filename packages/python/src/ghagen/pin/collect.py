"""Collect all pinnable ``uses:`` references from an App."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.pin.uses import UsesRef

if TYPE_CHECKING:
    from ghagen.app import App


def collect_uses_refs(app: App) -> set[str]:
    """Walk every registered item in *app* and return pinnable ``uses:`` strings.

    Traverses each Workflow/Action via :meth:`~ghagen.models._base.GhagenModel.walk`
    and collects pinnable refs from:

    - **Step** ``uses`` — action references (wherever a Step lives: workflow
      jobs or composite action ``runs.steps``)
    - **Job** ``uses`` — reusable workflow calls

    Skips local path refs (``./…``), docker image refs (``docker://…``), and
    refs already pinned to a 40-char SHA — see :meth:`UsesRef.is_pinnable`.
    """
    refs: set[str] = set()

    for item, _path in app._items:
        for _p, model in item.walk():
            # Only Step (action refs) and Job (reusable workflow calls) carry uses.
            uses = model.uses if isinstance(model, (Step, Job)) else None
            if isinstance(uses, str):
                parsed = UsesRef.parse(uses)
                if parsed is not None and parsed.is_pinnable:
                    refs.add(uses)

    return refs
