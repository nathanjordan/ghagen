"""Tests for GhagenModel.to_commented_map single-pass serialization.

Covers the exclude_none / exclude_unset semantics and the extras + comment
ordering that the single field walk must preserve (spec 0001).
"""

from ghagen._commented import with_comment, with_eol_comment
from ghagen.emitter.yaml_writer import dump_yaml
from ghagen.models.step import Step
from ghagen.models.trigger import On


def test_unset_fields_dropped():
    """Only fields the user set are emitted (exclude_unset)."""
    cm = Step(name="x").to_commented_map()
    assert list(cm.keys()) == ["name"]
    assert cm["name"] == "x"


def test_explicit_none_dropped():
    """A field explicitly set to None is dropped (exclude_none)."""
    cm = Step(name="x", run=None).to_commented_map()
    assert "run" not in cm
    assert list(cm.keys()) == ["name"]


def test_empty_workflow_dispatch_emits_null_key():
    """On with empty workflow_dispatch emits a present null key (Raw(None))."""
    cm = On(workflow_dispatch={}).to_commented_map()
    assert "workflow_dispatch" in cm
    assert cm["workflow_dispatch"] is None
    result = dump_yaml(cm)
    assert "workflow_dispatch:" in result
    assert "workflow_dispatch: {}" not in result


def test_serialization_alias_key_used():
    """serialization_alias fields emit under the aliased key."""
    cm = Step(if_="success()", working_directory="src").to_commented_map()
    assert "if" in cm
    assert "working-directory" in cm
    assert "if_" not in cm
    assert "working_directory" not in cm


def test_extras_appended_after_ordered_fields():
    """Extras land after the model's own ordered fields, in insertion order."""
    step = Step(name="x", extras={"custom": "v", "another": "w"})
    cm = step.to_commented_map()
    keys = list(cm.keys())
    assert keys[0] == "name"
    assert keys[-2:] == ["custom", "another"]


def test_commented_field_block_and_eol_comments():
    """Block/eol comments on Commented field values land on the right keys."""
    step = Step(
        name=with_comment("build", "the step name"),
        run=with_eol_comment("make", "run make"),
    )
    result = dump_yaml(step.to_commented_map())
    assert "# the step name" in result
    assert "run: make # run make" in result


def test_commented_extras_comments():
    """Comments on Commented extras values attach to the extra keys."""
    step = Step(
        name="x",
        extras={"custom": with_comment("v", "extra note")},
    )
    cm = step.to_commented_map()
    assert cm["custom"] == "v"
    result = dump_yaml(cm)
    assert "# extra note" in result
