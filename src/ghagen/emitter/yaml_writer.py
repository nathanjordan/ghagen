"""YAML emitter using ruamel.yaml with comment and key-ordering support."""

from __future__ import annotations

from io import StringIO
from typing import Any

from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen._raw import Raw


def unwrap_raw(value: Any) -> Any:
    """Recursively unwrap Raw instances to their inner values."""
    if isinstance(value, Raw):
        return value.value
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
    """
    is_valid_target = (isinstance(parent, CommentedSeq) and isinstance(key, int)) or (
        isinstance(parent, CommentedMap) and isinstance(key, str)
    )

    if not is_valid_target:
        return

    if comment is not None:
        parent.yaml_set_comment_before_after_key(key, before=comment)

    if eol_comment is not None:
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

    stream = StringIO()
    if header:
        stream.write(header)
        if not header.endswith("\n"):
            stream.write("\n")
    yaml.dump(data, stream)

    return stream.getvalue()
