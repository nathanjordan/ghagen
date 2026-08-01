"""Comment geometry: how far a ``#`` sits from the thing it annotates.

The single home for the two column decisions ghagen makes about comments —
the end-of-line gutter and the block-comment column — plus the rule for a
payload that cannot sit at end of line at all.

This is the Python peer of ``emitter/comment-geometry.ts``. Parity here is of
*role*, not of structure: ruamel.yaml resolves comment columns absolutely, at
dump time, from tokens already stamped onto the tree, so this port owns two
node-tree passes where TypeScript owns two string renderers. What is identical
is the stated rule — :data:`EOL_GUTTER` is 2 in both, and a newline-bearing
payload degrades to a block comment in both.

Coupling: this module reads ruamel-private structure (``node.ca.items`` and
``CommentToken.value`` / ``start_mark.column``), pinned against ruamel.yaml
0.19.1. Slot 2 of a ``CommentedMap`` entry and slot 0 of a ``CommentedSeq``
entry hold the EOL token; slot 1 holds the pre-key/pre-item block tokens.
"""

from __future__ import annotations

from typing import Any

from ruamel.yaml.comments import CommentedMap, CommentedSeq

# ruamel.yaml geometry assumed by :func:`~ghagen.emitter.yaml_writer.dump_yaml`
# (``best_map_indent=2``, ``best_sequence_indent=2``, ``sequence_dash_offset=0``,
# and indentless block sequences when a seq is a mapping value). These are the
# ONLY constants the pre-comment column alignment depends on; keeping them named
# and in one place means a change to the dump geometry has a single home.
_MAP_VALUE_INDENT = 2  # a sub-map indents by the mapping indent width
_SEQ_ITEM_INDENT = 2  # a seq item indents by the sequence indent width

#: Columns between the end of a line's content and the ``#`` of its EOL comment.
#:
#: Two, which is ruamel's own default and therefore the TypeScript port's.
EOL_GUTTER = 2


def render_eol_comment(text: str) -> str | None:
    """Render an end-of-line comment, gutter included.

    Returns ``None`` when *text* cannot sit at end of line — that is, when it
    contains a newline, which ruamel would emit as unparseable YAML. The caller
    (:mod:`ghagen.emitter.comments`) places such a payload as a block comment
    instead.

    ruamel's emitter writes one space of its own before a column-0 EOL token,
    so the returned string carries ``EOL_GUTTER - 1``. *text* may already carry
    its ``#`` — that is the contract of
    :meth:`ruamel.yaml.comments.CommentedBase.yaml_add_eol_comment`, and it
    makes this function idempotent over its own output, which
    :func:`_apply_eol_comment_gutter` relies on.
    """
    if "\n" in text:
        return None
    body = text if text.startswith("#") else f"# {text}"
    return " " * (EOL_GUTTER - 1) + body


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


def _apply_eol_comment_gutter(node: Any) -> None:
    """Restate every EOL comment token's gutter, independently of its neighbours.

    Left alone, ruamel decides the gutter in
    :meth:`~ruamel.yaml.comments.CommentedBase.yaml_add_eol_comment` by peeking
    at a NEIGHBOURING key's EOL token (``CommentedMap._yaml_get_column``): two
    columns normally, but one whenever an adjacent key in the same map happens
    to carry a comment, because the neighbour probe raises ``AttributeError``
    on a block-only comment slot and the ``' ' + comment`` line is skipped. The
    result is a gutter that depends on which *other* nodes carry comments.

    This pass overwrites that decision with :func:`render_eol_comment` at column
    0, so the gutter is a property of the comment and nothing else.
    """
    if not isinstance(node, (CommentedSeq, CommentedMap)):
        return
    # Slot 2 holds the EOL token for a map key, slot 0 for a seq index.
    eol_slot = 0 if isinstance(node, CommentedSeq) else 2
    items = getattr(node.ca, "items", None) or {}
    for entry in items.values():
        if not entry or len(entry) <= eol_slot:
            continue
        token = entry[eol_slot]
        if token is None:
            continue
        rendered = render_eol_comment(token.value.strip(" "))
        if rendered is None:
            continue
        token.value = rendered
        token.start_mark.column = 0
    children = node if isinstance(node, CommentedSeq) else node.values()
    for child in children:
        _apply_eol_comment_gutter(child)


def apply_comment_geometry(node: CommentedMap) -> None:
    """Apply every comment-column decision to *node* in place.

    The single entry point, called by
    :func:`~ghagen.emitter.yaml_writer.dump_yaml` immediately before the dump:
    block-comment columns first, then the end-of-line gutter.
    """
    _apply_pre_comment_columns(node, indent=0)
    _apply_eol_comment_gutter(node)
