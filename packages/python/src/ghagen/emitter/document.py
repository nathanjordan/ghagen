"""Document-level YAML emission — the emitter's public entry point.

:func:`emit` serializes a top-level :class:`~ghagen.models._base.Document`
(a Workflow or Action) to a complete YAML string, applying the header comment
and the document's own top-level block/EOL comment. All serialization recursion
lives in :mod:`ghagen.emitter.nodes`; this module only wraps the document root.
"""

from __future__ import annotations

from pathlib import Path

from ghagen.emitter.header import HeaderInput, format_header
from ghagen.emitter.nodes import _model_to_map, attach_root_comment
from ghagen.emitter.yaml_writer import dump_yaml
from ghagen.models._base import Document


def emit(
    document: Document,
    *,
    auto_dedent: bool,
    header: HeaderInput = None,
) -> str:
    """Serialize *document* to a complete YAML string.

    Args:
        document: The :class:`~ghagen.models._base.Document` (Workflow or
            Action) to serialize.
        auto_dedent: When true, each Step's ``run`` script is dedented at
            node-build time (ADR-0002). Required (no default): this internal
            entry is only ever called with a value threaded from ``App`` or the
            ``Document.to_yaml`` facade, so a default here would be dead surface
            that could drift from the TS port.
        header: Header comment. ``None`` emits no header; see
            :func:`~ghagen.emitter.header.format_header` for the other shapes.

    Returns:
        The complete YAML string.
    """
    cm = _model_to_map(document, auto_dedent=auto_dedent)

    # The document root's OWN comment, rendered on the map as a whole. Routed
    # through ghagen.emitter.nodes so comment attachment stays in one module
    # (see nodes.py's module docstring).
    attach_root_comment(cm, document)

    header_str = format_header(header, document._source_location)
    return dump_yaml(cm, header=header_str)


def emit_file(
    document: Document,
    path: str | Path,
    *,
    auto_dedent: bool,
    header: HeaderInput = None,
) -> None:
    """Write *document* as YAML to *path*, creating parent directories."""
    content = emit(document, auto_dedent=auto_dedent, header=header)
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
