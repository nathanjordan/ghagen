"""Tests for the comment-geometry module (``emitter/comment_geometry.py``).

The two node-tree passes are driven directly on hand-built ruamel nodes — the
first direct coverage either has had; until now the block-column pass was only
exercised indirectly through ``dump_yaml``. ``EOL_GUTTER``'s value is pinned
here, once, so the byte oracles elsewhere can stay literal.
"""

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen.emitter.comment_geometry import (
    EOL_GUTTER,
    _apply_eol_comment_gutter,
    _apply_pre_comment_columns,
    apply_comment_geometry,
    render_eol_comment,
)


def test_eol_gutter_is_two():
    """Two columns, which is ruamel's own default and the TypeScript port's."""
    assert EOL_GUTTER == 2


# --- render_eol_comment ---


def test_render_eol_comment_contributes_gutter_minus_one():
    """ruamel's emitter writes the last column itself, so the token carries one."""
    assert render_eol_comment("x") == " " * (EOL_GUTTER - 1) + "# x"
    assert render_eol_comment("x") == " # x"


def test_render_eol_comment_rejects_a_multiline_payload():
    """A newline cannot sit at end of line — ruamel would emit invalid YAML."""
    assert render_eol_comment("line one\nline two") is None


def test_render_eol_comment_passes_through_an_existing_hash():
    """The ``yaml_add_eol_comment`` contract; makes the pass idempotent."""
    assert render_eol_comment("# already") == " # already"
    assert render_eol_comment(render_eol_comment("x").strip(" ")) == " # x"


def test_render_eol_comment_leaves_an_inner_hash_alone():
    assert render_eol_comment("see issue # 42") == " # see issue # 42"


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
