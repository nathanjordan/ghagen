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
