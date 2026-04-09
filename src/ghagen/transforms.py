"""Model transform pipeline for synthesis-time transformations.

Transforms operate on deep copies of Pydantic models between user code
and YAML serialization.  Each transform receives a model and context,
mutates the model in place (or returns a replacement), and the result
is serialized to YAML.

Pipeline::

    models → deep copy → [Transform₁] → … → to_commented_map() → dump_yaml()
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ghagen.models.action import Action
    from ghagen.models.workflow import Workflow


@dataclass
class SynthContext:
    """Context available to transforms during synthesis."""

    workflow_key: str
    """The stem of the output filename (e.g. ``"ci"`` from ``ci.yml``)."""

    item_type: Literal["workflow", "action"]
    """Whether the item being transformed is a workflow or an action."""

    root: Path
    """The ``App.root`` directory."""


@runtime_checkable
class Transform(Protocol):
    """A model-level transform applied during synthesis.

    Implementations receive a *deep copy* of the original model and may
    mutate it freely. The returned value (which may be the same object)
    is passed to the next transform in the pipeline.
    """

    def __call__(
        self, item: Workflow | Action, ctx: SynthContext
    ) -> Workflow | Action: ...
