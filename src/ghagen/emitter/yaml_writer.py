"""YAML emitter using ruamel.yaml with comment and key-ordering support."""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import (
    LiteralScalarString,
    PlainScalarString,
    ScalarString,
)

from ghagen._raw import Raw


def unwrap_raw(value: Any) -> Any:
    """Recursively unwrap Raw instances to their inner values.

    Plain ``str`` values coming out of a ``Raw`` are wrapped in
    ``PlainScalarString`` so that the block-scalar auto-conversion pass in
    :func:`dump_yaml` leaves them alone — the ``Raw`` escape-hatch contract
    is to emit the inner value as-is.
    """
    if isinstance(value, Raw):
        inner = value.value
        if isinstance(inner, str) and not isinstance(inner, ScalarString):
            return PlainScalarString(inner)
        return inner
    if isinstance(value, dict):
        return {k: unwrap_raw(v) for k, v in value.items()}
    if isinstance(value, list):
        return [unwrap_raw(v) for v in value]
    return value


def to_ordered_commented_map(
    data: dict[str, Any],
    key_order: list[str],
) -> CommentedMap:
    """Convert a dict to a CommentedMap with keys in canonical order.

    Keys present in key_order come first in that order.
    Remaining keys follow in alphabetical order.
    """
    cm = CommentedMap()
    seen: set[str] = set()

    # Add keys in canonical order
    for key in key_order:
        if key in data:
            cm[key] = data[key]
            seen.add(key)

    # Add remaining keys alphabetically
    for key in sorted(data.keys()):
        if key not in seen:
            cm[key] = data[key]

    return cm


def attach_comment(
    parent: CommentedMap | CommentedSeq,
    key: str | int,
    comment: str | None = None,
    eol_comment: str | None = None,
) -> None:
    """Attach comments to a key in a CommentedMap or index in a CommentedSeq.

    Args:
        parent: The CommentedMap or CommentedSeq to attach comments to.
        key: The key (for maps) or index (for sequences) to attach comments to.
        comment: Block comment to place before the key.
        eol_comment: End-of-line comment to place after the value.

    Notes:
        When the target is a sequence index whose item is a non-empty
        ``CommentedMap``, ``eol_comment`` is redirected to the inner map's
        first key so the comment renders inline with that key rather than on
        the dash line (a ruamel.yaml quirk when EOL-commenting seq indices
        whose items are maps).

        Block comments are stored with a placeholder column of 0; the actual
        column is rewritten by :func:`_apply_pre_comment_columns` during
        :func:`dump_yaml` so the comment aligns with its containing item.
    """
    if isinstance(parent, CommentedMap) and isinstance(key, str):
        if comment is not None:
            parent.yaml_set_comment_before_after_key(key, before=comment)
        if eol_comment is not None:
            parent.yaml_add_eol_comment(eol_comment, key=key)
        return

    if isinstance(parent, CommentedSeq) and isinstance(key, int):
        if comment is not None:
            parent.yaml_set_comment_before_after_key(key, before=comment, indent=0)

        if eol_comment is not None:
            try:
                item = parent[key]
            except IndexError:
                item = None
            if isinstance(item, CommentedMap) and len(item) > 0:
                first_key = next(iter(item.keys()))
                item.yaml_add_eol_comment(eol_comment, key=first_key)
            else:
                parent.yaml_add_eol_comment(eol_comment, key=key)


def attach_field_comments(
    cm: CommentedMap,
    field_comments: dict[str, str] | None = None,
    field_eol_comments: dict[str, str] | None = None,
) -> None:
    """Attach per-field comments to a CommentedMap.

    Args:
        cm: The CommentedMap to attach comments to.
        field_comments: Mapping of field name to block comment.
        field_eol_comments: Mapping of field name to end-of-line comment.
    """
    if field_comments:
        for key, comment in field_comments.items():
            if key in cm:
                attach_comment(cm, key, comment=comment)

    if field_eol_comments:
        for key, comment in field_eol_comments.items():
            if key in cm:
                attach_comment(cm, key, eol_comment=comment)


def _apply_block_scalar_style(node: Any) -> None:
    """Recursively promote plain multiline strings to ``LiteralScalarString``.

    Any ``str`` containing ``\\n`` that is NOT already a ``ScalarString``
    subclass is replaced with a ``LiteralScalarString`` so it emits as a
    ``|`` block scalar. Values already wrapped in a ``ScalarString`` subclass
    (e.g., ``PlainScalarString`` from a ``Raw``) are left untouched so the
    ``Raw`` bypass is honored.
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
    ``CommentToken.start_mark.column`` — it does NOT auto-indent. This walker
    computes the correct column for every CommentedMap key and every
    CommentedSeq index and rewrites each pre-comment token accordingly so
    block comments align with the item they annotate.

    Assumes the default ruamel.yaml indent used by :func:`dump_yaml`:
    ``best_map_indent=2``, ``best_sequence_indent=2``,
    ``sequence_dash_offset=0``, and indentless block sequences when a seq is
    the value of a mapping key. If :func:`dump_yaml` ever exposes configurable
    indents, this walker's +0/+2 constants must be derived from those
    settings instead.
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
                _apply_pre_comment_columns(child, indent + 2)
        else:
            for value in node.values():
                # Sub-seqs are indentless under a map value (ruamel default);
                # sub-maps indent by the mapping-indent width (2).
                next_indent = indent if isinstance(value, CommentedSeq) else indent + 2
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
