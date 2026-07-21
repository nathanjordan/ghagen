"""Model transform pipeline for synthesis-time transformations.

Transforms operate on deep copies of Pydantic models between user code
and YAML serialization.  Each transform receives a model, mutates it in
place (or returns a replacement), and the result is serialized to YAML.

Pipeline::

    models → deep copy → [Transform₁] → … → to_commented_map() → dump_yaml()
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from ghagen.models.action import Action
    from ghagen.models.workflow import Workflow


@runtime_checkable
class Transform(Protocol):
    """A model-level transform applied during synthesis.

    Implementations receive a *deep copy* of the original model and may
    mutate it freely. The returned value (which may be the same object)
    is passed to the next transform in the pipeline.
    """

    def __call__(self, item: Workflow | Action) -> Workflow | Action: ...
