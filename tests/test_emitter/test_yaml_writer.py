"""Tests for the YAML emitter."""

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen._raw import Raw
from ghagen.emitter.yaml_writer import (
    attach_comment,
    dump_yaml,
    to_ordered_commented_map,
    unwrap_raw,
)


def test_unwrap_raw_scalar():
    assert unwrap_raw(Raw("hello")) == "hello"


def test_unwrap_raw_nested_dict():
    data = {"key": Raw("value"), "nested": {"inner": Raw(42)}}
    result = unwrap_raw(data)
    assert result == {"key": "value", "nested": {"inner": 42}}


def test_unwrap_raw_list():
    data = [Raw("a"), "b", Raw("c")]
    result = unwrap_raw(data)
    assert result == ["a", "b", "c"]


def test_unwrap_raw_passthrough():
    assert unwrap_raw("plain") == "plain"
    assert unwrap_raw(42) == 42
    assert unwrap_raw(None) is None


def test_to_ordered_commented_map():
    data = {"c": 3, "a": 1, "b": 2}
    cm = to_ordered_commented_map(data, ["a", "b", "c"])
    assert list(cm.keys()) == ["a", "b", "c"]


def test_to_ordered_commented_map_unknown_keys():
    data = {"z": 26, "a": 1, "m": 13}
    cm = to_ordered_commented_map(data, ["a"])
    assert list(cm.keys()) == ["a", "m", "z"]


def test_attach_block_comment():
    cm = CommentedMap({"key": "value"})
    attach_comment(cm, "key", comment="This is a comment")
    yaml_str = dump_yaml(cm)
    assert "# This is a comment" in yaml_str


def test_attach_eol_comment():
    cm = CommentedMap({"key": "value"})
    attach_comment(cm, "key", eol_comment="inline note")
    yaml_str = dump_yaml(cm)
    assert "inline note" in yaml_str


def test_attach_comment_to_seq():
    seq = CommentedSeq(["a", "b", "c"])
    attach_comment(seq, 1, comment="Before b")
    # Just verify it doesn't raise - comment rendering is ruamel's job


def test_dump_yaml_basic():
    cm = CommentedMap({"name": "test", "value": 42})
    result = dump_yaml(cm)
    assert "name: test" in result
    assert "value: 42" in result


def test_dump_yaml_with_header():
    cm = CommentedMap({"key": "value"})
    result = dump_yaml(cm, header="# My header\n")
    assert result.startswith("# My header\n")
    assert "key: value" in result


# --- Sequence item comment behavior tests ---
# These tests document current ruamel.yaml behavior for comments on sequence items.
# Known limitations:
#   - EOL comments on map-items render on a separate line instead of inline
#   - Block comments on map-items are not indented to match surrounding context


def test_eol_comment_on_scalar_seq_item():
    """EOL comments on scalar sequence items render inline correctly."""
    seq = CommentedSeq(["main", "develop"])
    attach_comment(seq, 0, eol_comment="primary branch")
    cm = CommentedMap({"branches": seq})
    result = dump_yaml(cm)
    assert "- main  # primary branch" in result


def test_block_comment_on_scalar_seq_item():
    """Block comments on scalar sequence items render before the item."""
    seq = CommentedSeq(["main", "develop"])
    attach_comment(seq, 1, comment="feature branch")
    cm = CommentedMap({"branches": seq})
    result = dump_yaml(cm)
    assert "# feature branch" in result
    # The comment appears before the second item
    lines = result.strip().split("\n")
    comment_idx = next(i for i, line in enumerate(lines) if "feature branch" in line)
    develop_idx = next(i for i, line in enumerate(lines) if "develop" in line)
    assert comment_idx < develop_idx


def test_eol_comment_on_map_seq_item_known_limitation():
    """EOL comments on map sequence items render on a separate line.

    Known ruamel.yaml limitation. Ideally this would render as:
        - uses: actions/checkout@v4  # checkout step
    But ruamel.yaml renders it as:
        -  # checkout step
          uses: actions/checkout@v4
    """
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    seq.append(CommentedMap({"run": "echo hello"}))
    attach_comment(seq, 0, eol_comment="checkout step")
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    # The comment text is present
    assert "# checkout step" in result
    # Known limitation: comment is NOT inline with the key
    assert "uses: actions/checkout@v4  # checkout step" not in result


def test_block_comment_on_map_seq_item_known_limitation():
    """Block comments on map sequence items are not indented.

    The comment renders at column 0 regardless of nesting depth.
    """
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    seq.append(CommentedMap({"run": "echo hello"}))
    attach_comment(seq, 1, comment="Run the tests")
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    assert "# Run the tests" in result
    # The comment appears before the second item
    lines = result.strip().split("\n")
    comment_idx = next(i for i, line in enumerate(lines) if "Run the tests" in line)
    run_idx = next(i for i, line in enumerate(lines) if "run: echo hello" in line)
    assert comment_idx < run_idx
