"""Tests for the comment-geometry module (``emitter/comment_geometry.py``).

The two node-tree passes are driven directly on hand-built ruamel nodes — the
first direct coverage either has had; until now the block-column pass was only
exercised indirectly through ``dump_yaml``.

``EOL_GUTTER`` and the ``render_eol_comment`` vectors are NOT pinned here as
literals. They come from ``schema/comment-geometry.yml``, which the TypeScript
peer (``emitter/comment-geometry.test.ts``) reads too. A literal in each port is
two mirrors, not a binding: changing one port's renderer and its own literal
together leaves the other port green and the emitted comment column silently
divergent. One oracle, two readers.
"""

from typing import Any

import pytest
from ghagen_schema.paths import SCHEMA_DIR
from ruamel.yaml import YAML
from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen.emitter.comment_geometry import (
    EOL_GUTTER,
    _apply_eol_comment_gutter,
    _apply_pre_comment_columns,
    apply_comment_geometry,
    render_eol_comment,
)

COMMENT_GEOMETRY_PATH = SCHEMA_DIR / "comment-geometry.yml"


def _load_geometry() -> dict[str, Any]:
    return YAML(typ="safe").load(COMMENT_GEOMETRY_PATH.read_text(encoding="utf-8"))


def test_eol_gutter_matches_the_shared_table():
    """Two columns, which is ruamel's own default and the TypeScript port's."""
    assert _load_geometry()["eol_gutter"] == EOL_GUTTER


# --- render_eol_comment ---


@pytest.mark.parametrize(
    "vector",
    _load_geometry()["eol_comment"],
    ids=[repr(v["payload"]) for v in _load_geometry()["eol_comment"]],
)
def test_render_eol_comment_matches_the_shared_vectors(vector: dict[str, Any]):
    """The one function both ports share by signature and by contract.

    Covers the gutter, the ``#`` pass-through that keeps the Python gutter pass
    idempotent over its own output, an inner ``#`` (content, not a marker), and
    the newline payload that cannot sit at end of line at all.
    """
    assert render_eol_comment(vector["payload"]) == vector["rendered"]


def test_render_eol_comment_contributes_gutter_minus_one():
    """ruamel's emitter writes the last column itself, so the token carries one."""
    assert render_eol_comment("x") == " " * (EOL_GUTTER - 1) + "# x"


def test_render_eol_comment_is_idempotent_over_its_own_output():
    """What the ``#`` pass-through in the shared table buys the gutter pass."""
    assert render_eol_comment(render_eol_comment("x").strip(" ")) == " # x"


# --- _apply_pre_comment_columns ---


def test_pre_comment_columns_indents_a_nested_map_key():
    inner = CommentedMap({"name": "Test"})
    inner.yaml_set_comment_before_after_key("name", before="note")
    root = CommentedMap({"jobs": CommentedMap({"test": inner})})
    _apply_pre_comment_columns(root, indent=0)
    # jobs (0) -> test (+2) -> name (+2)
    assert inner.ca.items["name"][1][0].start_mark.column == 4


def test_pre_comment_columns_indents_a_seq_item():
    seq = CommentedSeq([CommentedMap({"run": "x"})])
    seq.yaml_set_comment_before_after_key(0, before="note", indent=0)
    root = CommentedMap({"steps": seq})
    _apply_pre_comment_columns(root, indent=0)
    # A block seq under a map value is indentless, so the dash keeps the
    # parent's column.
    assert seq.ca.items[0][1][0].start_mark.column == 0


def test_pre_comment_columns_overwrites_the_placeholder():
    cm = CommentedMap({"a": 1})
    cm.yaml_set_comment_before_after_key("a", before="note", indent=17)
    _apply_pre_comment_columns(cm, indent=0)
    assert cm.ca.items["a"][1][0].start_mark.column == 0


# --- _apply_eol_comment_gutter ---


def test_eol_gutter_pass_normalises_a_one_column_token():
    cm = CommentedMap({"a": 1})
    cm.yaml_add_eol_comment("note", key="a", column=0)
    assert cm.ca.items["a"][2].value == "# note"  # ruamel's one-column form
    _apply_eol_comment_gutter(cm)
    assert cm.ca.items["a"][2].value == " # note"
    assert cm.ca.items["a"][2].start_mark.column == 0


def test_eol_gutter_pass_is_idempotent():
    cm = CommentedMap({"a": 1})
    cm.yaml_add_eol_comment("note", key="a", column=0)
    _apply_eol_comment_gutter(cm)
    _apply_eol_comment_gutter(cm)
    assert cm.ca.items["a"][2].value == " # note"


def test_eol_gutter_pass_reaches_a_seq_index_token():
    seq = CommentedSeq(["main"])
    seq.yaml_add_eol_comment("primary", key=0, column=0)
    root = CommentedMap({"branches": seq})
    _apply_eol_comment_gutter(root)
    # Slot 0 holds the EOL token for a seq index (slot 2 for a map key).
    assert seq.ca.items[0][0].value == " # primary"


def test_eol_gutter_pass_leaves_block_tokens_alone():
    cm = CommentedMap({"a": 1})
    cm.yaml_set_comment_before_after_key("a", before="block")
    _apply_eol_comment_gutter(cm)
    assert cm.ca.items["a"][1][0].value == "# block\n"


# --- apply_comment_geometry: the single entry point ---


def test_apply_comment_geometry_runs_both_passes():
    inner = CommentedMap({"name": "Test", "needs": "lint"})
    inner.yaml_set_comment_before_after_key("needs", before="wait", indent=9)
    inner.yaml_add_eol_comment("job note", key="name", column=0)
    root = CommentedMap({"jobs": CommentedMap({"test": inner})})
    apply_comment_geometry(root)
    assert inner.ca.items["needs"][1][0].start_mark.column == 4
    assert inner.ca.items["name"][2].value == " # job note"
