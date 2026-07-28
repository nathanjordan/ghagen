"""Behaviour tests for the public observation surface ``to_data``.

``to_data`` is THE supported way to observe a single model's emitted structure.
These tests pin its interface contract (keys, values, order, aliasing, extras,
Raw unwrapping, comments, error mode) directly, per proposal 02.
"""

from __future__ import annotations

import io

import pytest
from ruamel.yaml import YAML

from ghagen import (
    Job,
    Matrix,
    On,
    PushTrigger,
    Raw,
    Step,
    Strategy,
    Workflow,
    with_comment,
    with_eol_comment,
)
from ghagen.emitter import CommentNode, to_data
from ghagen.models.job import Defaults, DefaultsRun


def test_returns_plain_dict():
    assert to_data(Step(uses="actions/checkout@v4")) == {"uses": "actions/checkout@v4"}


def test_absence_is_asserted_by_equality():
    # An exhaustive == asserts both presence and absence of keys.
    assert to_data(Step(name="Run tests", run="pytest")) == {
        "name": "Run tests",
        "run": "pytest",
    }


def test_field_aliasing_via_spec():
    assert to_data(Step(if_="success()"))["if"] == "success()"


def test_with_field_alias():
    data = to_data(Step(uses="actions/setup-node@v4", with_={"node-version": "20"}))
    assert data == {"uses": "actions/setup-node@v4", "with": {"node-version": "20"}}


def test_canonical_key_ordering():
    step = Step(
        timeout_minutes=5,
        name="Build",
        uses="actions/checkout@v4",
        id="co",
    )
    assert list(to_data(step)) == ["id", "name", "uses", "timeout-minutes"]


def test_extras_merged_after_ordered_keys():
    step = Step(name="Build", extras={"custom": "x"})
    data = to_data(step)
    assert list(data) == ["name", "custom"]
    assert data["custom"] == "x"


def test_raw_unwrapped_to_inner_value():
    data = to_data(Step(shell=Raw("future-shell")))
    assert data == {"shell": "future-shell"}
    # comments=False yields no framework wrapper types.
    assert not isinstance(data["shell"], Raw)
    assert type(data["shell"]) is str


def test_comments_false_unwraps_commented():
    step = Step(uses=with_eol_comment("actions/checkout@v4", "pinned"))
    assert to_data(step) == {"uses": "actions/checkout@v4"}


def test_comments_true_surfaces_eol_comment():
    step = Step(uses=with_eol_comment("actions/checkout@v4", "v4"))
    assert to_data(step, comments=True)["uses"] == CommentNode(
        "actions/checkout@v4", eol_comment="v4"
    )


def test_comments_true_surfaces_block_comment():
    step = Step(name=with_comment("Build", "the build step"))
    assert to_data(step, comments=True)["name"] == CommentNode(
        "Build", comment="the build step"
    )


def test_comments_true_leaves_uncommented_values_plain():
    step = Step(name="Build", uses=with_eol_comment("actions/checkout@v4", "v4"))
    data = to_data(step, comments=True)
    assert data["name"] == "Build"
    assert isinstance(data["uses"], CommentNode)


def test_nested_model_emitted_as_plain_dict():
    job = Job(runs_on="ubuntu-latest", steps=[Step(run="pytest")])
    data = to_data(job)
    assert data["runs-on"] == "ubuntu-latest"
    assert data["steps"] == [{"run": "pytest"}]


def test_nested_model_own_comment_surfaced_with_comments_true():
    job = Job(runs_on="ubuntu-latest", steps=[Step(run="pytest", comment="run it")])
    data = to_data(job, comments=True)
    assert data["steps"] == [CommentNode({"run": "pytest"}, comment="run it")]


def test_non_model_raises_type_error():
    with pytest.raises(TypeError):
        to_data({"not": "a model"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_data("just a string")  # type: ignore[arg-type]


def test_bare_step_run_dedented_with_auto_dedent():
    # Parity with the ruamel recursion: a bare Step's run dedents wherever it is
    # encountered, not only inside a Document.
    data = to_data(Step(run="  echo one\n  echo two"), auto_dedent=True)
    assert data["run"] == "echo one\necho two"


def test_deep_structure_matches_emitted_yaml():
    # Deep structural cross-check (proposal 02): the parsed emitted YAML tree
    # must equal to_data's output for a RICH document, so the two duplicated
    # recursions cannot diverge on exclude/unwrap/present-null/dedent — not just
    # top-level ordering. Comments are dropped by the YAML parse, so to_data runs
    # with comments off; auto_dedent matches the ``to_yaml`` default-on.
    wf = Workflow(
        name="CI",
        on=On(
            push=PushTrigger(branches=["main"]),
            workflow_dispatch={},  # present-null empty map
            extras={"merge_group": {}},  # extra on the alphabetical On spec
        ),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                defaults=Defaults(
                    run=DefaultsRun(shell=with_comment("bash", "login shell"))
                ),
                strategy=Strategy(
                    matrix=Matrix(extras={"python-version": ["3.11", "3.12"]})
                ),
                steps=[
                    Step(uses=with_eol_comment("actions/checkout@v4", "pinned")),
                    Step(name="run", shell=Raw("bash"), run="  echo hi\n  echo bye"),
                ],
            )
        },
    )
    yaml = YAML(typ="safe")
    parsed = yaml.load(io.StringIO(wf.to_yaml(header=None)))
    assert to_data(wf, auto_dedent=True) == parsed
