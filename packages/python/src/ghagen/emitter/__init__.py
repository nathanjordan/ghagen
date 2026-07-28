"""The ghagen emitter — the single owner of model → YAML serialization.

Public surface:

- :func:`emit` — serialize a :class:`~ghagen.models._base.Document` to a YAML
  string.
- :func:`emit_file` — the same, written to a file.
- :func:`to_data` — emit any model to plain Python data, the supported surface
  for observing a single model's emitted structure.
- :class:`CommentNode` — the backend-neutral representation of a value plus its
  attached comment, produced by ``to_data(..., comments=True)``.

All serialization recursion lives inside this package
(:mod:`ghagen.emitter.nodes` for the ruamel backend,
:mod:`ghagen.emitter.data` for the plain observation surface): the emitter
imports ``models``, never the reverse. The public names are resolved lazily via
:pep:`562` module ``__getattr__`` so that a ``models`` module importing
:mod:`ghagen.emitter.header` (a leaf that pulls no models) does not trigger the
``nodes`` / ``data`` → ``models`` import at ``models`` load time — the one seam
that would otherwise re-form the models↔emitter cycle this package exists to
break.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["emit", "emit_file", "to_data", "CommentNode"]

if TYPE_CHECKING:
    from ghagen.emitter.data import CommentNode, to_data
    from ghagen.emitter.document import emit, emit_file


def __getattr__(name: str) -> Any:
    if name in ("emit", "emit_file"):
        from ghagen.emitter import document

        return getattr(document, name)
    if name in ("to_data", "CommentNode"):
        from ghagen.emitter import data

        return getattr(data, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
