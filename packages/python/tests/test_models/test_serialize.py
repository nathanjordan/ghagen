"""Tests for the emitter's single-pass model serialization, via ``to_data``.

Covers the exclude_none / exclude_unset semantics and the extras + comment
ordering that the single field walk must preserve (ADR-0001), observed through
the public ``to_data`` surface rather than the private recursion core.
"""

from ghagen._commented import with_comment, with_eol_comment
from ghagen.emitter import CommentNode, to_data
from ghagen.models.job import Defaults, DefaultsRun, Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger, WorkflowDispatchTrigger
from ghagen.models.workflow import Workflow


def test_unset_fields_dropped():
    """Only fields the user set are emitted (exclude_unset)."""
    assert to_data(Step(name="x")) == {"name": "x"}


def test_explicit_none_dropped():
    """A field explicitly set to None is dropped (exclude_none)."""
    assert to_data(Step(name="x", run=None)) == {"name": "x"}


def test_empty_workflow_dispatch_emits_present_null_key():
    """On with empty workflow_dispatch emits a present null key.

    Driven by ``ON_SPEC.present_null_when_empty`` in the Emitter, not a
    model-layer ``Raw(None)`` mutation.
    """
    data = to_data(On(workflow_dispatch=WorkflowDispatchTrigger()))
    assert "workflow_dispatch" in data
    assert data["workflow_dispatch"] is None
    # Formatting (bare null key, not ``{}``) is a YAML concern — assert it on
    # the emitted string via a wrapping workflow.
    wf = Workflow(name="W", on=On(workflow_dispatch=WorkflowDispatchTrigger()))
    yaml = wf.to_yaml(header=None)
    assert "workflow_dispatch:" in yaml
    assert "workflow_dispatch: {}" not in yaml


def test_boolean_workflow_dispatch_not_present_null():
    """A boolean workflow_dispatch is a scalar, not an empty map — left as-is."""
    assert to_data(On(workflow_dispatch=True))["workflow_dispatch"] is True


def test_on_emits_alphabetically_interleaving_extras():
    """order="alphabetical" sorts all keys; a dynamic extra event interleaves."""
    data = to_data(
        On(
            workflow_run={"types": ["completed"]},
            push=PushTrigger(branches=["main"]),
            extras={"merge_group": {}},
        )
    )
    assert list(data) == ["merge_group", "push", "workflow_run"]


def test_defaults_run_shell_comment_preserved():
    """A Commented wrapper on defaults.run.shell survives to observed data.

    Parity guard mirroring the TypeScript comment-drop fix: `run` is a proper
    DefaultsRun model, so shell/working-directory flow through the normal
    emitter path and their comments survive.
    """
    data = to_data(
        Defaults(run=DefaultsRun(shell=with_comment("bash", "login shell"))),
        comments=True,
    )
    assert data["run"]["shell"] == CommentNode("bash", comment="login shell")


def test_defaults_run_shell_comment_in_emitted_yaml():
    """The defaults.run.shell comment reaches the emitted YAML string.

    Byte-level oracle mirroring TS ``job.test.ts`` "emits the run.shell comment
    into YAML": ``to_data`` observes the wrapper, but only the rendered string
    proves the comment survives the ruamel backend passes.
    """
    wf = Workflow(
        name="W",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                defaults=Defaults(
                    run=DefaultsRun(shell=with_comment("bash", "login shell"))
                ),
                steps=[Step(run="echo hi")],
            )
        },
    )
    assert "# login shell" in wf.to_yaml(header=None)


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
