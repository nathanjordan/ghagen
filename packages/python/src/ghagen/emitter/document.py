"""Document-level YAML emission — the emitter's public entry point.

:func:`emit` serializes a top-level :class:`~ghagen.models._base.Document`
(a Workflow or Action) to a complete YAML string, applying the header comment
and the document's own top-level block/EOL comment. All serialization recursion
lives in :mod:`ghagen.emitter.nodes`; this module only wraps the document root.
"""

from __future__ import annotations

from pathlib import Path

from ghagen.emitter.comments import attach_model_comment
from ghagen.emitter.header import HeaderInput, format_header
from ghagen.emitter.nodes import _model_to_map
from ghagen.emitter.yaml_writer import dump_yaml
from ghagen.models._base import Document


def emit(
    document: Document,
    *,
    auto_dedent: bool = False,
    header: HeaderInput = None,
) -> str:
    """Serialize *document* to a complete YAML string.

    Args:
        document: The :class:`~ghagen.models._base.Document` (Workflow or
            Action) to serialize.
        auto_dedent: When true, each Step's ``run`` script is dedented at
            node-build time (ADR-0002). Off by default; the ``Document.to_yaml``
            facade defaults it on.
        header: Header comment. ``None`` emits no header; see
            :func:`~ghagen.emitter.header.format_header` for the other shapes.

    Returns:
        The complete YAML string.
    """
    cm = _model_to_map(document, auto_dedent=auto_dedent)

    # The document root's OWN comment, rendered on the map as a whole — the same
    # helper that closes the nested map-value gap.
    attach_model_comment(cm, comment=document.comment, eol_comment=document.eol_comment)

    header_str = format_header(header, document._source_location)
    return dump_yaml(cm, header=header_str)


def emit_file(
    document: Document,
    path: str | Path,
    *,
    auto_dedent: bool = False,
    header: HeaderInput = None,
) -> None:
    """Write *document* as YAML to *path*, creating parent directories."""
    content = emit(document, auto_dedent=auto_dedent, header=header)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
