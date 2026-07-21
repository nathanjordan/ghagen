"""Comment attachment: the single owner of how a comment lands on a ruamel node.

Every path by which a YAML comment reaches a node routes through this module:

- :func:`attach` — the low-level primitive. Attaches a block and/or EOL comment
  to a map key or a seq index. Owns the map-vs-seq dispatch, the seq-item map
  EOL-redirect quirk, and the block-comment placeholder column (rewritten later
  by :func:`~ghagen.emitter.yaml_writer.dump_yaml`).
- :func:`attach_model_comment` — a model's OWN comment, rendered on the map as a
  whole: block before the first key, EOL after the last value. Used for the
  Document root AND every nested map-value model.

This is the Python peer of ``emitter/comments.ts``.
"""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap, CommentedSeq


def attach(
    parent: CommentedMap | CommentedSeq,
    key: str | int,
    *,
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
        column is rewritten by
        :func:`~ghagen.emitter.yaml_writer._apply_pre_comment_columns` during
        :func:`~ghagen.emitter.yaml_writer.dump_yaml` so the comment aligns
        with its containing item.
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


def attach_model_comment(
    node: CommentedMap,
    *,
    comment: str | None = None,
    eol_comment: str | None = None,
) -> None:
    """Attach a model's OWN comment, rendered on the map as a whole.

    A block ``comment`` is placed before the map's first key; an
    ``eol_comment`` is placed after the map's last value (its last key's line).
    Used for the Document root AND every nested map-value model, so a model's
    own comment renders regardless of the container it sits in.

    A no-op on an empty map (no key to anchor the comment to).
    """
    if not node:
        return
    keys = list(node.keys())
    if not keys:
        return
    if comment is not None:
        attach(node, keys[0], comment=comment)
    if eol_comment is not None:
        attach(node, keys[-1], eol_comment=eol_comment)
