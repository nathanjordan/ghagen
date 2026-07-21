"""Final YAML rendering: block-scalar promotion, comment-column alignment, dump.

The value → node recursion lives in :mod:`ghagen.emitter.nodes`; this module
owns the two whole-tree passes ruamel needs before serialization and the
:func:`dump_yaml` call itself.
"""

from __future__ import annotations

from io import StringIO
from typing import Any

from pydantic.fields import FieldInfo
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import (
    LiteralScalarString,
    ScalarString,
)

# ruamel.yaml geometry assumed by :func:`dump_yaml` (``best_map_indent=2``,
# ``best_sequence_indent=2``, ``sequence_dash_offset=0``, and indentless block
# sequences when a seq is a mapping value). These are the ONLY constants the
# pre-comment column alignment depends on; keeping them named and in one place
# means a change to the dump geometry has a single home to update.
_MAP_VALUE_INDENT = 2  # a sub-map indents by the mapping indent width
_SEQ_ITEM_INDENT = 2  # a seq item indents by the sequence indent width


def _yaml_key(field_name: str, field_info: FieldInfo) -> str:
    """Resolve the YAML key for a model field: serialization_alias wins,
    then a string validation_alias, then alias, else the field name."""
    alias = field_info.alias or field_name
    if isinstance(field_info.validation_alias, str):
        alias = field_info.validation_alias
    return field_info.serialization_alias or alias


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


def _apply_pre_comment_columns(node: Any, indent: int = 0) -> None:
    """Rewrite the column of every pre-item/pre-key block comment in the tree.

    ruamel.yaml's emitter renders pre-comments at exactly
    ``CommentToken.start_mark.column`` — it does NOT auto-indent. This walker is
    the single owner of the *final* column decision: it computes the correct
    column for every CommentedMap key and every CommentedSeq index and rewrites
    each pre-comment token accordingly so block comments align with the item
    they annotate. The placeholder column stamped by
    :func:`ghagen.emitter.comments.attach` is always overwritten here.

    Uses the ruamel geometry constants :data:`_MAP_VALUE_INDENT` /
    :data:`_SEQ_ITEM_INDENT`; block sequences under a mapping value are
    indentless (ruamel default), so a sub-seq keeps its parent's indent.
    """
    if isinstance(node, (CommentedSeq, CommentedMap)):
        items = getattr(node.ca, "items", None) or {}
        for entry in items.values():
            if entry and len(entry) > 1 and entry[1]:
                for token in entry[1]:
                    if token is not None:
                        token.start_mark.column = indent
        if isinstance(node, CommentedSeq):
            for child in node:
                _apply_pre_comment_columns(child, indent + _SEQ_ITEM_INDENT)
        else:
            for value in node.values():
                # Sub-seqs are indentless under a map value (ruamel default);
                # sub-maps indent by the mapping-indent width.
                next_indent = (
                    indent
                    if isinstance(value, CommentedSeq)
                    else indent + _MAP_VALUE_INDENT
                )
                _apply_pre_comment_columns(value, next_indent)


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
    # 2. Rewrite block-comment columns so pre-item / pre-key comments align
    #    with their containing node instead of sticking to column 0.
    _apply_block_scalar_style(data)
    _apply_pre_comment_columns(data, indent=0)

    stream = StringIO()
    if header:
        stream.write(header)
        if not header.endswith("\n"):
            stream.write("\n")
    yaml.dump(data, stream)

    return stream.getvalue()
