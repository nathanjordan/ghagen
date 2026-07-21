"""Tests for the YAML rendering passes and the node dispatcher.

``dump_yaml`` and the block-scalar / comment-column passes are the emitter's
whole-tree rendering stage and are exercised directly. The value → node
dispatch (`_to_node`, `unwrap_raw`, `to_ordered_commented_map`) lives in
:mod:`ghagen.emitter.nodes`; those are low-level probes into the emitter's
recursion core, kept because the behaviors (Raw see-through, key ordering,
seq-item comment placement) are cheaper to pin at the node level than to
reverse-engineer from rendered YAML.
"""

import pytest
from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import LiteralScalarString, PlainScalarString

from ghagen._commented import with_comment
from ghagen._raw import Raw
from ghagen.emitter.nodes import (
    _model_to_map,
    _to_node,
    to_ordered_commented_map,
    unwrap_raw,
)
from ghagen.emitter.yaml_writer import (
    _apply_block_scalar_style,
    _yaml_key,
    dump_yaml,
)
from ghagen.models.step import Step


def _node(value):
    """Dispatch a value through the emitter's node core (auto_dedent off)."""
    return _to_node(value, auto_dedent=False)


# --- unwrap_raw: Raw see-through (single home for the Raw → scalar rule) ---


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


# --- to_ordered_commented_map: canonical key ordering ---


def test_to_ordered_commented_map():
    data = {"c": 3, "a": 1, "b": 2}
    cm = to_ordered_commented_map(data, ["a", "b", "c"])
    assert list(cm.keys()) == ["a", "b", "c"]


def test_to_ordered_commented_map_unknown_keys():
    data = {"z": 26, "a": 1, "m": 13}
    cm = to_ordered_commented_map(data, ["a"])
    assert list(cm.keys()) == ["a", "m", "z"]


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


# --- Multiline string block-scalar auto-conversion tests ---


def test_multiline_string_becomes_literal_block():
    """A plain multiline str is auto-converted to a | literal block scalar."""
    cm = CommentedMap({"run": "python -m pytest\ncoverage report\n"})
    result = dump_yaml(cm)
    assert "run: |" in result
    assert "  python -m pytest" in result
    assert "  coverage report" in result


def test_single_line_string_stays_plain():
    """Single-line strings are not promoted to block scalars."""
    cm = CommentedMap({"run": "echo hello"})
    result = dump_yaml(cm)
    assert "run: echo hello" in result
    assert "|" not in result


def test_multiline_string_no_trailing_newline_strips():
    """A multiline string without a trailing newline uses |- (strip-chomping)."""
    cm = CommentedMap({"run": "python -m pytest\ncoverage report"})
    result = dump_yaml(cm)
    assert "run: |-" in result
    assert "  python -m pytest" in result
    assert "  coverage report" in result


def test_raw_multiline_bypasses_auto_conversion():
    """Raw[str] multiline values are NOT promoted to literal block scalars."""
    cm = CommentedMap()
    cm["x"] = unwrap_raw(Raw("a\nb"))
    _apply_block_scalar_style(cm)
    assert not isinstance(cm["x"], LiteralScalarString)


def test_nested_multiline_string_conversion():
    """Multiline strings nested inside sequences and maps are converted."""
    seq = CommentedSeq()
    seq.append(CommentedMap({"run": "line1\nline2\n"}))
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    assert "run: |" in result
    assert "  line1" in result
    assert "  line2" in result


# --- _to_node recursive dispatcher tests (low-level probes) ---


@pytest.mark.parametrize("value", ["x", 42, True, None])
def test_to_node_scalar_identity(value):
    """Plain scalars pass through _to_node unchanged."""
    assert _node(value) == value


def test_to_node_raw_scalar():
    """Raw scalars unwrap to their inner value."""
    assert _node(Raw("x")) == "x"


def test_to_node_raw_multiline_is_plain_scalar():
    """Raw multiline str becomes a PlainScalarString (bypasses block-literal cast)."""
    node = _node(Raw("a\nb"))
    assert isinstance(node, PlainScalarString)
    assert not isinstance(node, LiteralScalarString)
    assert str(node) == "a\nb"


def test_to_node_commented_scalar_returns_inner():
    """A Commented-wrapped scalar yields the inner value (comment is caller's job)."""
    assert _node(with_comment("hello", "note")) == "hello"


def test_to_node_dict_becomes_commented_map():
    """A plain dict becomes a CommentedMap with recursively converted values."""
    node = _node({"a": Raw("1"), "b": {"c": 2}})
    assert isinstance(node, CommentedMap)
    assert node["a"] == "1"
    assert isinstance(node["b"], CommentedMap)
    assert node["b"]["c"] == 2


def test_to_node_commented_map_passthrough():
    """An existing CommentedMap is passed through unchanged (same object)."""
    cm = CommentedMap({"k": "v"})
    assert _node(cm) is cm


def test_to_node_list_of_scalars_becomes_seq():
    """A list of scalars becomes a CommentedSeq."""
    node = _node(["a", "b"])
    assert isinstance(node, CommentedSeq)
    assert list(node) == ["a", "b"]


def test_to_node_list_with_model_item_comments():
    """Item comments from GhagenModel entries attach at the right index."""
    steps = [
        Step(uses="actions/checkout@v4", comment="checkout"),
        Step(run="echo hi", eol_comment="say hi"),
    ]
    seq = _node(steps)
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    assert "# checkout" in result
    assert "- run: echo hi  # say hi" in result


def test_to_node_ghagen_model_matches_model_to_map():
    """A GhagenModel node has the same keys/values as _model_to_map for it."""
    step = Step(name="build", run="make")
    node = _node(step)
    assert isinstance(node, CommentedMap)
    assert node == _model_to_map(step)


# --- _yaml_key alias resolver tests (spec/alias agreement helper) ---


def test_yaml_key_plain_field_name():
    """A field with no alias resolves to its own name."""
    assert _yaml_key("name", Step.model_fields["name"]) == "name"


def test_yaml_key_serialization_alias():
    """serialization_alias wins for output keys."""
    assert _yaml_key("if_", Step.model_fields["if_"]) == "if"
    assert (
        _yaml_key("working_directory", Step.model_fields["working_directory"])
        == "working-directory"
    )


def test_yaml_key_validation_alias_string(monkeypatch):
    """A string validation_alias (no serialization_alias) is used."""
    from pydantic.fields import FieldInfo

    fi = FieldInfo()
    monkeypatch.setattr(fi, "alias", None, raising=False)
    monkeypatch.setattr(fi, "validation_alias", "valias", raising=False)
    monkeypatch.setattr(fi, "serialization_alias", None, raising=False)
    assert _yaml_key("field", fi) == "valias"


def test_yaml_key_alias_fallback(monkeypatch):
    """alias is used when no serialization_alias or string validation_alias."""
    from pydantic.fields import FieldInfo

    fi = FieldInfo()
    monkeypatch.setattr(fi, "alias", "the_alias", raising=False)
    monkeypatch.setattr(fi, "validation_alias", None, raising=False)
    monkeypatch.setattr(fi, "serialization_alias", None, raising=False)
    assert _yaml_key("field", fi) == "the_alias"
