"""Tests for the emitter's single-pass model serialization, via ``to_data``.

Covers the exclude_none / exclude_unset semantics and the extras + comment
ordering that the single field walk must preserve (ADR-0001), observed through
the public ``to_data`` surface rather than the private recursion core.
"""

from ghagen._commented import with_comment, with_eol_comment
from ghagen.emitter import CommentNode, to_data
from ghagen.models.job import Defaults, DefaultsRun, Job
from ghagen.models.step import Step
from ghagen.models.trigger import ON_SPEC, On
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
    data = to_data(On(workflow_dispatch={}))
    assert "workflow_dispatch" in data
    assert data["workflow_dispatch"] is None
    # Formatting (bare null key, not ``{}``) is a YAML concern — assert it on
    # the emitted string via a wrapping workflow.
    yaml = Workflow(name="W", on=On(workflow_dispatch={})).to_yaml(header=None)
    assert "workflow_dispatch:" in yaml
    assert "workflow_dispatch: {}" not in yaml


def test_boolean_workflow_dispatch_not_present_null():
    """A boolean workflow_dispatch is a scalar, not an empty map — left as-is."""
    assert to_data(On(workflow_dispatch=True))["workflow_dispatch"] is True


def test_explicit_none_event_is_unset_not_present():
    """``None`` on an ``on:`` event means *unset*, never "present, no filters".

    docs/issues/04. The two ports used to disagree about this and the
    disagreement was not cosmetic: Python dropped the key (``on: {}``, a
    workflow that fires on nothing) while TypeScript kept it (a workflow that
    fires on ``create``). One word, one meaning, both ports; ``{}`` is how a
    caller asks for the event with no filters. Peer:
    ``packages/typescript/src/models/trigger.test.ts``.
    """
    assert to_data(On(create=None)) == {}
    yaml = Workflow(name="W", on=On(create=None)).to_yaml(header=None)
    assert "\non: {}\n" in yaml
    assert "create" not in yaml


def test_every_on_event_present_nulls_an_empty_map():
    """Every ``on:`` event key emits GitHub's bare ``key:`` for an empty map.

    ``ON_SPEC.present_null_when_empty`` is derived from ``ON_SPEC.yaml_keys``,
    so this walks the whole key set rather than restating a second list of
    names: an event added to ``yaml_keys`` is covered here the moment it is
    declared. It was a one-element allowlist (``workflow_dispatch``) until
    docs/issues/04, so every other event emitted ``create: {}``.

    ``schedule`` is the one key skipped, and it is not an exception to the
    rule: its value is a *list*, which ``resolves_to_empty_map`` never treats
    as an empty map.
    """
    for field_name, yaml_key in ON_SPEC.yaml_keys.items():
        if field_name == "schedule":
            assert to_data(On(schedule=[]))["schedule"] == []
            continue
        assert to_data(On(**{field_name: {}}))[yaml_key] is None, yaml_key
        yaml = Workflow(name="W", on=On(**{field_name: {}})).to_yaml(header=None)
        assert f"\n  {yaml_key}:\n" in yaml, yaml_key
        assert f"{yaml_key}: {{}}" not in yaml, yaml_key


def test_on_emits_alphabetically_interleaving_extras():
    """order="alphabetical" sorts all keys; a dynamic extra event interleaves."""
    data = to_data(
        On(
            workflow_run={"types": ["completed"]},
            push={"branches": ["main"]},
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
        on=On(push={"branches": ["main"]}),
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
