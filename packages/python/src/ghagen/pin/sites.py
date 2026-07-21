"""UsesSite — the single traversal policy over a Document's ``uses:`` refs.

Pin's :mod:`~ghagen.pin.collect` (read) and :mod:`~ghagen.pin.transform`
(replace) both iterate :class:`UsesSite` objects, so the knowledge of *which*
models carry a ``uses:`` field, and *how* to reach it through a possible
:class:`~ghagen._commented.Commented` wrapper, lives here alone. A third
``uses``-bearing model is one entry in :func:`iter_uses_sites`; the consumers
need no change.
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ghagen._commented import Commented, is_commented
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.pin.uses import UsesRef

if TYPE_CHECKING:
    from ghagen.models._base import Document, GhagenModel

#: The field name carrying a pinnable ``uses:`` on every uses-bearing model.
_USES_FIELD = "uses"


@dataclass
class UsesSite:
    """One ``uses:`` occurrence inside a Document.

    Carries the parsed :class:`~ghagen.pin.uses.UsesRef` (which knows whether
    it is **Pinnable**) and can :meth:`replace` the ref in place, threading the
    new value back through any :class:`~ghagen._commented.Commented` wrapper on
    the field.
    """

    ref: UsesRef
    """The parsed ``owner/repo[/path]@ref`` reference."""

    uses: str
    """The original ``uses:`` string, as authored (any wrapper peeled)."""

    _model: GhagenModel = field(repr=False)
    _field: str = field(repr=False)

    def replace(self, new: str) -> None:
        """Rewrite this ``uses:`` field to *new*.

        The original ref is attached as an end-of-line comment, and any block
        comment already on the field is preserved, so the emitted YAML keeps
        its annotations.
        """
        current = getattr(self._model, self._field)
        block = current.comment if is_commented(current) else None
        wrapped = Commented(new, comment=block, eol_comment=self.ref.ref)
        setattr(self._model, self._field, wrapped)


def iter_uses_sites(document: Document) -> Iterator[UsesSite]:
    """Yield a :class:`UsesSite` for every parseable ``uses:`` in *document*.

    Walks the model tree via :meth:`~ghagen.models._base.GhagenModel.walk` and
    selects the ``uses`` field of every :class:`~ghagen.models.step.Step`
    (action references) and :class:`~ghagen.models.job.Job` (reusable-workflow
    calls), wherever they live — workflow jobs or composite-action
    ``runs.steps``. The field value is read through any
    :class:`~ghagen._commented.Commented` wrapper.

    Values that do not parse as an ``owner/repo[/path]@ref`` reference — local
    ``./…`` paths, ``docker://…`` images, or bare strings — yield no site.
    A ref already written as a SHA *does* yield a site, whose
    ``ref.is_pinnable`` is ``False``.
    """
    for _path, model in document.walk():
        if not isinstance(model, (Step, Job)):
            continue
        value = getattr(model, _USES_FIELD, None)
        if is_commented(value):
            value = value.value
        if not isinstance(value, str):
            continue
        ref = UsesRef.parse(value)
        if ref is None:
            continue
        yield UsesSite(ref=ref, uses=value, _model=model, _field=_USES_FIELD)
