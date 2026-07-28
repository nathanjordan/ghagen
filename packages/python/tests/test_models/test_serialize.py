"""Tests for the emitter's single-pass model serialization, via ``to_data``.

Covers the exclude_none / exclude_unset semantics and the extras + comment
ordering that the single field walk must preserve (ADR-0001), observed through
the public ``to_data`` surface rather than the private recursion core.
"""

from ghagen._commented import with_comment, with_eol_comment
from ghagen.emitter import CommentNode, to_data
from ghagen.models.step import Step
from ghagen.models.trigger import On
from ghagen.models.workflow import Workflow


def test_unset_fields_dropped():
    """Only fields the user set are emitted (exclude_unset)."""
    assert to_data(Step(name="x")) == {"name": "x"}


def test_explicit_none_dropped():
    """A field explicitly set to None is dropped (exclude_none)."""
    assert to_data(Step(name="x", run=None)) == {"name": "x"}


def test_empty_workflow_dispatch_emits_present_null_key():
    """On with empty workflow_dispatch emits a present null key (Raw(None))."""
    data = to_data(On(workflow_dispatch={}))
    assert "workflow_dispatch" in data
    assert data["workflow_dispatch"] is None
    # Formatting (bare null key, not ``{}``) is a YAML concern — assert it on
    # the emitted string via a wrapping workflow.
    yaml = Workflow(name="W", on=On(workflow_dispatch={})).to_yaml(header=None)
    assert "workflow_dispatch:" in yaml
    assert "workflow_dispatch: {}" not in yaml


def test_spec_yaml_key_used():
    """Fields emit under the YAML key declared in the model's ModelSpec."""
    data = to_data(Step(if_="success()", working_directory="src"))
    assert "if" in data
    assert "working-directory" in data
    assert "if_" not in data
    assert "working_directory" not in data


def test_extras_appended_after_ordered_fields():
    """Extras land after the model's own ordered fields, in insertion order."""
    data = to_data(Step(name="x", extras={"custom": "v", "another": "w"}))
    keys = list(data)
    assert keys[0] == "name"
    assert keys[-2:] == ["custom", "another"]


def test_commented_field_block_and_eol_comments():
    """Block/eol comments on Commented field values are observable as data."""
    data = to_data(
        Step(
            name=with_comment("build", "the step name"),
            run=with_eol_comment("make", "run make"),
        ),
        comments=True,
    )
    assert data["name"] == CommentNode("build", comment="the step name")
    assert data["run"] == CommentNode("make", eol_comment="run make")


def test_commented_extras_comments():
    """Comments on Commented extras values attach to the extra keys."""
    step = Step(name="x", extras={"custom": with_comment("v", "extra note")})
    # comments=False unwraps to the plain value.
    assert to_data(step)["custom"] == "v"
    # comments=True surfaces the attached comment as data.
    assert to_data(step, comments=True)["custom"] == CommentNode(
        "v", comment="extra note"
    )
