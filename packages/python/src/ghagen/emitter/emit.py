"""Document-level YAML emission.

Serializes a top-level model (a :class:`~ghagen.models._base.Document`) to a
complete YAML string or file, applying the header comment and the model's
top-level block comment. These are the file-producing serializers; nested
models expose only :meth:`~ghagen.models._base.GhagenModel.to_commented_map`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ghagen.emitter.comments import attach_model_comment
from ghagen.emitter.header import DEFAULT, HeaderInput, format_header
from ghagen.emitter.yaml_writer import dump_yaml

if TYPE_CHECKING:
    from ghagen.models._base import GhagenModel


def _dedent_steps(model: GhagenModel) -> GhagenModel:
    """Return a deep copy of *model* with every Step's ``run`` dedented.

    Dedent is a serialization-time normalization (ADR-0002): ``Step.run``
    holds the raw string until emit, so this pass walks the tree — steps
    nested inside jobs *and* composite-action runs — and rewrites ``run``
    on a copy, leaving the caller's model untouched.
    """
    from ghagen._dedent import dedent_script
    from ghagen.models.step import Step

    working = model.model_copy(deep=True)
    for _path, node in working.walk():
        if isinstance(node, Step) and isinstance(node.run, str):
            node.run = dedent_script(node.run)
    return working


def to_yaml(
    model: GhagenModel, header: HeaderInput = DEFAULT, *, auto_dedent: bool = True
) -> str:
    """Serialize *model* to a complete YAML string.

    Applies the model's ``comment`` above the first key and resolves the
    ``header`` (see :func:`~ghagen.emitter.header.format_header` for the four
    accepted shapes).

    When *auto_dedent* is true (the default), every Step's ``run`` script is
    dedented on a private copy of the model before serialization; the
    caller's model is never mutated.
    """
    if auto_dedent:
        model = _dedent_steps(model)

    cm = model.to_commented_map()

    # The root model's OWN comment, rendered on the map as a whole — the same
    # helper that closes the nested map-value gap.
    attach_model_comment(cm, comment=model.comment, eol_comment=model.eol_comment)

    header_str = format_header(header, model._source_location)
    return dump_yaml(cm, header=header_str)


def to_yaml_file(
    model: GhagenModel,
    path: str | Path,
    header: HeaderInput = DEFAULT,
    *,
    auto_dedent: bool = True,
) -> None:
    """Write *model* as YAML to *path*, creating parent directories."""
    content = to_yaml(model, header, auto_dedent=auto_dedent)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
