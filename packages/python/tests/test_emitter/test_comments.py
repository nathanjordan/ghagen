"""Tests for the comment-attachment module (``emitter/comments.py``).

Drives the module directly on hand-built ruamel nodes — no Document / model
round-trip. Assertions are split between the raw comment structures on
``node.ca`` (the primitive's job) and the rendered output via ``dump_yaml``
(the seq-item ruamel quirks and block-comment column alignment).
"""

from ruamel.yaml.comments import CommentedMap, CommentedSeq

from ghagen.emitter.comments import attach, attach_model_comment
from ghagen.emitter.yaml_writer import dump_yaml


def _block_token(node, key):
    """The pre-key block CommentToken list stored on ``node.ca`` for ``key``."""
    return node.ca.items[key][1]


def _eol_token(node, key):
    """The post-value EOL CommentToken stored on ``node.ca`` for a map key."""
    return node.ca.items[key][2]


# --- attach: map key primitive ---


def test_attach_block_on_map_key():
    cm = CommentedMap({"key": "value"})
    attach(cm, "key", comment="block here")
    tokens = _block_token(cm, "key")
    assert tokens is not None
    assert "block here" in tokens[0].value


def test_attach_eol_on_map_key():
    cm = CommentedMap({"key": "value"})
    attach(cm, "key", eol_comment="inline note")
    assert "inline note" in _eol_token(cm, "key").value


def test_attach_block_and_eol_on_map_key():
    cm = CommentedMap({"key": "value"})
    attach(cm, "key", comment="above", eol_comment="beside")
    assert "above" in _block_token(cm, "key")[0].value
    assert "beside" in _eol_token(cm, "key").value


def test_attach_none_is_noop():
    cm = CommentedMap({"key": "value"})
    attach(cm, "key")
    assert "key" not in cm.ca.items


# --- attach: seq index primitive ---


def test_attach_block_on_seq_index():
    seq = CommentedSeq(["a", "b", "c"])
    attach(seq, 1, comment="before b")
    assert "before b" in seq.ca.items[1][1][0].value


def test_attach_eol_on_scalar_seq_index():
    """EOL on a scalar seq item is stored on the seq index itself."""
    seq = CommentedSeq(["a", "b"])
    attach(seq, 0, eol_comment="beside a")
    assert "beside a" in seq.ca.items[0][0].value


def test_attach_eol_on_map_seq_index_redirects_to_first_key():
    """EOL on a seq index whose item is a non-empty map is redirected to the
    item's first key (the ruamel quirk this module encapsulates)."""
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4", "with": "x"}))
    attach(seq, 0, eol_comment="checkout step")
    # Not on the seq index...
    assert seq.ca.items == {}
    # ...but on the item's first key.
    assert "checkout step" in _eol_token(seq[0], "uses").value


def test_attach_eol_on_empty_map_seq_index_falls_back():
    """EOL on a seq index whose item is an empty map falls back to the index."""
    seq = CommentedSeq()
    seq.append(CommentedMap())
    attach(seq, 0, eol_comment="empty item")
    assert "empty item" in seq.ca.items[0][0].value


# --- attach_model_comment: a model's own comment on the map as a whole ---


def test_attach_model_comment_block_on_first_key():
    cm = CommentedMap({"first": 1, "last": 2})
    attach_model_comment(cm, comment="model block")
    assert "model block" in _block_token(cm, "first")[0].value
    assert "last" not in cm.ca.items


def test_attach_model_comment_eol_on_last_value():
    cm = CommentedMap({"first": 1, "last": 2})
    attach_model_comment(cm, eol_comment="model eol")
    assert "model eol" in _eol_token(cm, "last").value


def test_attach_model_comment_block_and_eol():
    cm = CommentedMap({"first": 1, "middle": 2, "last": 3})
    attach_model_comment(cm, comment="above", eol_comment="beside")
    assert "above" in _block_token(cm, "first")[0].value
    assert "beside" in _eol_token(cm, "last").value


def test_attach_model_comment_empty_map_is_noop():
    cm = CommentedMap()
    attach_model_comment(cm, comment="x", eol_comment="y")
    assert cm.ca.items == {}


# --- Rendered seq-item behavior (ruamel quirks, via dump_yaml) ---


def test_eol_comment_on_scalar_seq_item_renders_inline():
    """EOL comments on scalar sequence items render inline correctly."""
    seq = CommentedSeq(["main", "develop"])
    attach(seq, 0, eol_comment="primary branch")
    cm = CommentedMap({"branches": seq})
    result = dump_yaml(cm)
    assert "- main  # primary branch" in result


def test_block_comment_on_scalar_seq_item_renders_before():
    """Block comments on scalar sequence items render before the item."""
    seq = CommentedSeq(["main", "develop"])
    attach(seq, 1, comment="feature branch")
    cm = CommentedMap({"branches": seq})
    result = dump_yaml(cm)
    assert "# feature branch" in result
    lines = result.strip().split("\n")
    comment_idx = next(i for i, line in enumerate(lines) if "feature branch" in line)
    develop_idx = next(i for i, line in enumerate(lines) if "develop" in line)
    assert comment_idx < develop_idx


def test_eol_comment_on_map_seq_item_renders_inline():
    """EOL comments on map-seq items render inline with the first key."""
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    seq.append(CommentedMap({"run": "echo hello"}))
    attach(seq, 0, eol_comment="checkout step")
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    assert "- uses: actions/checkout@v4  # checkout step" in result


def test_eol_comment_on_empty_map_seq_item_falls_back():
    """EOL comment on an empty map-seq item falls back to the seq index."""
    seq = CommentedSeq()
    seq.append(CommentedMap())
    attach(seq, 0, eol_comment="empty item")
    cm = CommentedMap({"items": seq})
    result = dump_yaml(cm)
    assert "empty item" in result


def test_block_comment_on_map_seq_item_is_indented():
    """Block comments on map-seq items render between items at the dash column."""
    seq = CommentedSeq()
    seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    seq.append(CommentedMap({"run": "echo hello"}))
    attach(seq, 1, comment="Run the tests")
    cm = CommentedMap({"steps": seq})
    result = dump_yaml(cm)
    lines = result.split("\n")
    comment_idx = next(i for i, line in enumerate(lines) if "Run the tests" in line)
    assert lines[comment_idx] == "# Run the tests"
    assert lines[comment_idx + 1] == "- run: echo hello"


def test_block_comment_on_nested_map_seq_item_is_indented():
    """Block comment on a deeply nested seq item is indented to the dash column."""
    inner_seq = CommentedSeq()
    inner_seq.append(CommentedMap({"uses": "actions/checkout@v4"}))
    inner_seq.append(CommentedMap({"name": "Test", "run": "pytest"}))
    attach(inner_seq, 1, comment="Run tests")

    cm = CommentedMap()
    jobs = CommentedMap()
    test_job = CommentedMap()
    test_job["runs-on"] = "ubuntu-latest"
    test_job["steps"] = inner_seq
    jobs["test"] = test_job
    cm["jobs"] = jobs

    result = dump_yaml(cm)
    assert "    # Run tests" in result
    lines = result.split("\n")
    comment_line_idx = next(i for i, line in enumerate(lines) if "# Run tests" in line)
    assert lines[comment_line_idx] == "    # Run tests"
    assert lines[comment_line_idx + 1] == "    - name: Test"


def test_block_comment_on_nested_map_field_is_indented():
    """Block comment on a nested CommentedMap field is indented to the key column."""
    inner = CommentedMap({"name": "Test", "needs": "lint"})
    attach(inner, "needs", comment="Wait for lint to pass")

    cm = CommentedMap()
    jobs = CommentedMap()
    jobs["test"] = inner
    cm["jobs"] = jobs

    result = dump_yaml(cm)
    lines = result.split("\n")
    comment_idx = next(
        i for i, line in enumerate(lines) if "Wait for lint to pass" in line
    )
    assert lines[comment_idx] == "    # Wait for lint to pass"
    assert lines[comment_idx + 1].startswith("    needs:")


def test_attach_model_comment_renders_block_and_eol_via_dump():
    """attach_model_comment renders a block before the first key and an EOL on
    the last value when the map is dumped."""
    cm = CommentedMap({"name": "Lint", "runs-on": "ubuntu-latest"})
    attach_model_comment(cm, comment="Run linters before tests", eol_comment="job note")
    result = dump_yaml(cm)
    lines = result.split("\n")
    assert lines[0] == "# Run linters before tests"
    assert lines[1].startswith("name: Lint")
    assert "runs-on: ubuntu-latest # job note" in result
