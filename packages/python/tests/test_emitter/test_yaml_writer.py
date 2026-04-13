"""Tests for the YAML emitter."""

from ruamel.yaml.comments import CommentedMap, CommentedSeq
from ruamel.yaml.scalarstring import LiteralScalarString

from ghagen._raw import Raw
from ghagen.emitter.yaml_writer import (
    _apply_block_scalar_style,
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


def test_eol_comment_on_map_seq_item_renders_inline():
    """EOL comments on map-seq items render inline with the first key."""
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    seq.append(CommentedMap({"run": "echo hello"}))
    attach_comment(seq, 0, eol_comment="checkout step")
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    assert "- uses: actions/checkout@v4  # checkout step" in result


def test_eol_comment_on_empty_map_seq_item_falls_back():
    """EOL comment on an empty map-seq item falls back to the seq index."""
    seq = CommentedSeq()
    seq.append(CommentedMap())
    attach_comment(seq, 0, eol_comment="empty item")
    cm = CommentedMap({"items": seq})
    # Should not raise; comment text is present somewhere.
    result = dump_yaml(cm)
    assert "empty item" in result


def test_block_comment_on_map_seq_item_is_indented():
    """Block comments on map-seq items render between items at the dash column."""
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    seq.append(CommentedMap({"run": "echo hello"}))
    attach_comment(seq, 1, comment="Run the tests")
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    lines = result.split("\n")
    # Top-level "steps" key: dashes are indentless under the map value, so
    # column 0. The comment line must start at column 0, before the second
    # item's dash.
    comment_idx = next(i for i, line in enumerate(lines) if "Run the tests" in line)
    assert lines[comment_idx] == "# Run the tests"
    assert lines[comment_idx + 1] == "- run: echo hello"


def test_block_comment_on_nested_map_seq_item_is_indented():
    """Block comment on a deeply nested seq item is indented to the dash column."""
    inner_seq = CommentedSeq()
    inner_seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    inner_seq.append(CommentedMap({"name": "Test", "run": "pytest"}))
    attach_comment(inner_seq, 1, comment="Run tests")

    cm = CommentedMap()
    jobs = CommentedMap()
    test_job = CommentedMap()
    test_job["runs-on"] = "ubuntu-latest"
    test_job["steps"] = inner_seq
    jobs["test"] = test_job
    cm["jobs"] = jobs

    result = dump_yaml(cm)
    # jobs (map) -> test (map, indent +2=4) -> steps (indentless seq, stays
    # at 4). The dash and the comment should both sit at column 4.
    assert "    # Run tests" in result
    comment_line_idx = next(
        i for i, line in enumerate(result.split("\n")) if "# Run tests" in line
    )
    lines = result.split("\n")
    assert lines[comment_line_idx] == "    # Run tests"
    assert lines[comment_line_idx + 1] == "    - name: Test"


def test_block_comment_on_nested_map_field_is_indented():
    """Block comment on a nested CommentedMap field is indented to the key column."""
    inner = CommentedMap({"name": "Test", "needs": "lint"})
    attach_comment(inner, "needs", comment="Wait for lint to pass")

    cm = CommentedMap()
    jobs = CommentedMap()
    jobs["test"] = inner
    cm["jobs"] = jobs

    result = dump_yaml(cm)
    # jobs (map, 0) -> test (map, +2=2) -> needs (key at col 4)
    lines = result.split("\n")
    comment_idx = next(
        i for i, line in enumerate(lines) if "Wait for lint to pass" in line
    )
    assert lines[comment_idx] == "    # Wait for lint to pass"
    assert lines[comment_idx + 1].startswith("    needs:")


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
