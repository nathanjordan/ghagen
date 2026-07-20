"""Document-level YAML emission.

Serializes a top-level model (a :class:`~ghagen.models._base.Document`) to a
complete YAML string or file, applying the header comment and the model's
top-level block comment. These are the file-producing serializers; nested
models expose only :meth:`~ghagen.models._base.GhagenModel.to_commented_map`.
"""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ghagen.emitter.header import DEFAULT, HeaderInput, format_header
from ghagen.emitter.yaml_writer import attach_comment, dump_yaml

if TYPE_CHECKING:
    from ghagen.models._base import GhagenModel


def to_yaml(model: GhagenModel, header: HeaderInput = DEFAULT) -> str:
    """Serialize *model* to a complete YAML string.

    Applies the model's ``comment`` above the first key and resolves the
    ``header`` (see :func:`~ghagen.emitter.header.format_header` for the four
    accepted shapes).
    """
    cm = model.to_commented_map()

    if model.comment and cm:
        attach_comment(cm, next(iter(cm.keys())), comment=model.comment)

    header_str = format_header(header, model._source_location)
    return dump_yaml(cm, header=header_str)


def to_yaml_file(
    model: GhagenModel, path: str | Path, header: HeaderInput = DEFAULT
) -> None:
    """Write *model* as YAML to *path*, creating parent directories."""
    content = to_yaml(model, header)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
