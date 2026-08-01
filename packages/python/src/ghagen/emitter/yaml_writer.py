"""Final YAML rendering: block-scalar promotion, dump.

The value → node recursion lives in :mod:`ghagen.emitter.nodes` and every
comment-column decision lives in :mod:`ghagen.emitter.comment_geometry`; this
module owns the block-scalar pass and the :func:`dump_yaml` call itself.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap
from ruamel.yaml.scalarstring import (
    LiteralScalarString,
    ScalarString,
)

from ghagen.emitter.comment_geometry import apply_comment_geometry


def _apply_block_scalar_style(node: Any) -> None:
    """Recursively promote plain multiline strings to ``LiteralScalarString``.

    Any ``str`` containing ``\\n`` that is NOT already a ``ScalarString``
    subclass is replaced with a ``LiteralScalarString`` so it emits as a
    ``|`` block scalar. Values already wrapped in a ``ScalarString`` subclass
    (e.g., ``PlainScalarString`` from a ``Raw`` — see
    :func:`ghagen._raw.raw_scalar`) are left untouched so the ``Raw`` bypass is
    honored.
    """
    if isinstance(node, dict):
        for key in list(node.keys()):
            value = node[key]
            if (
                isinstance(value, str)
                and not isinstance(value, ScalarString)
                and "\n" in value
            ):
                node[key] = LiteralScalarString(value)
            else:
                _apply_block_scalar_style(value)
    elif isinstance(node, list):
        for idx in range(len(node)):
            value = node[idx]
            if (
                isinstance(value, str)
                and not isinstance(value, ScalarString)
                and "\n" in value
            ):
                node[idx] = LiteralScalarString(value)
            else:
                _apply_block_scalar_style(value)


def dump_yaml(
    data: CommentedMap,
    header: str | None = None,
) -> str:
    """Dump a CommentedMap to a YAML string.

    Args:
        data: The CommentedMap to serialize.
        header: Optional header comment to prepend (already formatted with #).

    Returns:
        The YAML string.
    """
    yaml = YAML()
    yaml.default_flow_style = False
    yaml.preserve_quotes = True
    yaml.width = 4096  # Prevent line wrapping

    # Auto-formatting passes:
    # 1. Promote multiline plain strings to | literal block scalars.
    # 2. Apply every comment-column decision (block columns, EOL gutter).
    _apply_block_scalar_style(data)
    apply_comment_geometry(data)

    stream = StringIO()
    if header:
        stream.write(header)
        if not header.endswith("\n"):
            stream.write("\n")
    yaml.dump(data, stream)

    return stream.getvalue()
