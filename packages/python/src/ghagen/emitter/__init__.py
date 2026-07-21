"""The ghagen emitter — the single owner of model → YAML serialization.

Public surface:

- :func:`emit` — serialize a :class:`~ghagen.models._base.Document` to a YAML
  string.
- :func:`emit_file` — the same, written to a file.

All serialization recursion lives inside this package
(:mod:`ghagen.emitter.nodes`): the emitter imports ``models``, never the
reverse. ``emit`` / ``emit_file`` are resolved lazily via :pep:`562` module
``__getattr__`` so that a ``models`` module importing
:mod:`ghagen.emitter.header` (a leaf that pulls no models) does not trigger the
``nodes`` → ``models`` import at ``models`` load time — the one seam that would
otherwise re-form the models↔emitter cycle this package exists to break.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

__all__ = ["emit", "emit_file"]

if TYPE_CHECKING:
    from ghagen.emitter.document import emit, emit_file


def __getattr__(name: str) -> Any:
    if name in __all__:
        from ghagen.emitter import document

        return getattr(document, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
