"""The synthesis pipeline: Document + transforms -> emitted YAML text.

This module is the single ``Document in -> transformed clone -> YAML text out``
seam. It is *filesystem-free* and *root-free*: it carries each Document's
registered path through untouched so the caller knows where the text goes, but
it never joins a root, creates a directory, or reads/writes a file. ``App.synth``
and ``App.check`` are thin consumers that differ only in what they do with each
``(path, text)`` pair (write vs. diff).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from pathlib import Path

from ghagen.emitter.document import emit
from ghagen.emitter.header import HeaderInput
from ghagen.models.action import Action
from ghagen.models.workflow import Workflow
from ghagen.transforms import Transform

#: The emittable Documents. In Python ``Document`` is a base *class*; the union
#: of its two concrete subclasses is the value the pipeline (and the ``Transform``
#: protocol) actually flows — the counterpart of the TS ``Document`` type alias.
Document = Workflow | Action


@dataclass(frozen=True)
class Rendered:
    """One Document rendered to YAML, tagged with its registered path."""

    #: The rel path as registered on ``App``; opaque to the pipeline.
    path: Path
    #: The complete emitted YAML.
    text: str


def apply_transforms(document: Document, transforms: Sequence[Transform]) -> Document:
    """Deep-copy *document* and fold *transforms* over the copy, in order.

    The input is never mutated. With no transforms the copy is skipped and the
    original is returned (callers must treat the result as read-only).
    """
    if not transforms:
        return document
    working = document.model_copy(deep=True)
    for transform in transforms:
        working = transform(working)
    return working


def render(
    items: Sequence[tuple[Document, Path]],
    transforms: Sequence[Transform],
    *,
    header: HeaderInput,
    auto_dedent: bool,
) -> list[Rendered]:
    """Render every ``(document, path)`` pair to YAML.

    Invariants:
      * Transforms apply in list order: index 0 first, last index last. This is
        the whole ordering contract — the pipeline does not sort or reorder.
      * Each document is rendered from an independent deep copy; the caller's
        models are never mutated.
      * ``header`` and ``auto_dedent`` are threaded straight into ``emit`` on
        every document (ADR-0002: no global carries them).
    """
    return [
        Rendered(
            path=path,
            text=emit(
                apply_transforms(document, transforms),
                header=header,
                auto_dedent=auto_dedent,
            ),
        )
        for document, path in items
    ]
