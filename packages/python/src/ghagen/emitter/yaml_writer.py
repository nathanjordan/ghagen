"""YAML emitter using ruamel.yaml with comment and key-ordering support."""

from __future__ import annotations

from io import StringIO
from typing import Any

from pydantic.fields import FieldInfo
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import (
    LiteralScalarString,
    PlainScalarString,
    ScalarString,
)

from ghagen._commented import Commented
from ghagen._raw import Raw
from ghagen.emitter.comments import attach, attach_model_comment


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


def _to_yaml_seq(items: list[Any]) -> CommentedSeq:
    """Serialize a list to a CommentedSeq, attaching each GhagenModel item's
    OWN comment on the seq index.

    Model items are serialized via :meth:`~GhagenModel.to_commented_map`
    directly (not through :func:`to_yaml_node`) so their own comment lands
    once, on the seq index (``attach(seq, idx, ...)``) — the container
    decision for a list entry. Routing model items through
    :func:`to_yaml_node` instead would additionally stamp the comment on the
    child map's first key, double-attaching it.
    """
    from ghagen.models._base import GhagenModel  # local: avoid import cycle

    seq = CommentedSeq()
    for idx, item in enumerate(items):
        if isinstance(item, GhagenModel):
            seq.append(item.to_commented_map())
            attach(seq, idx, comment=item.comment, eol_comment=item.eol_comment)
        else:
            seq.append(to_yaml_node(item))
    return seq


def to_yaml_node(value: Any) -> Any:
    """Convert any model value to a YAML node in one recursive pass.

    Python peer of TypeScript's ``toYamlValue``. This is the single place a
    Commented / Raw / GhagenModel / dict / list / scalar becomes a ruamel node.
    """
    from ghagen.models._base import GhagenModel  # local: avoid import cycle

    if isinstance(value, Commented):
        return to_yaml_node(value.value)
    if isinstance(value, Raw):
        # Route through unwrap_raw to keep PlainScalarString wrapping of
        # Raw[str] (bypasses the block-scalar auto-cast).
        return unwrap_raw(value)
    if isinstance(value, GhagenModel):
        child = value.to_commented_map()
        # A model as a map value renders its own comment on the map as a whole
        # (block before first key, EOL after last value). Seq items never reach
        # here — _to_yaml_seq serializes them directly and attaches on the index.
        attach_model_comment(
            child, comment=value.comment, eol_comment=value.eol_comment
        )
        return child
    if isinstance(value, CommentedMap):
        return value
    if isinstance(value, dict):
        cm = CommentedMap()
        for k, v in value.items():
            cm[k] = to_yaml_node(v)
        return cm
    if isinstance(value, list):
        return _to_yaml_seq(value)
    return unwrap_raw(value)


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
