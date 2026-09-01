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
    WorkflowDispatchTrigger,
    with_comment,
    with_eol_comment,
)
from ghagen.emitter import CommentNode, to_data
from ghagen.models.job import Defaults, DefaultsRun
from ghagen_schema.paths import EXPECTED_DIR


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


def test_extras_astral_plane_keys_order_by_code_point():
    """``On(extras=...)`` (docs/issues/23 item 5) -- the only reachable path.

    The issue's own example pair: ``"\\u{1F600}"`` (an astral-plane key,
    U+1F600) and ``"＀"`` (U+FF00, a BMP key). ``On.SPEC.order ==
    "alphabetical"``, so every extras key merges into the same sort
    ``order_entries`` runs on typed fields, and these two disagree on where
    they land depending on whether the comparison is by Unicode code point
    (Python's native ``str`` ordering) or by UTF-16 code unit (the pre-fix
    TypeScript ``.sort()``): the BMP char's single code unit (0xFF00) is
    numerically *larger* than the astral char's leading surrogate (0xD83D),
    even though the astral char's actual code point (0x1F600) is larger
    still. ``fixtures/expected/on_extras_astral_order.txt`` is the shared
    oracle the TypeScript peer asserts the same order against.
    """
    on = On(
        push=PushTrigger(),
        extras={"＀_event": {}, "\U0001f600_event": {}},
    )

    fixture_path = EXPECTED_DIR / "on_extras_astral_order.txt"
    expected = fixture_path.read_text(encoding="utf-8").splitlines()
    assert list(to_data(on)) == expected


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


def test_present_null_fires_when_the_empty_model_carries_its_own_comment():
    """A model comment must not change the *structure* ``to_data`` reports.

    ``present_null_when_empty`` tested emptiness on the already-converted value,
    and a commented model converts to a ``CommentNode``, which is not a ``dict``
    — so the rule silently stopped firing and ``to_data(comments=True)``
    reported ``{}`` where ``to_data()`` and ``emit`` both report null.
    """
    on = On(workflow_dispatch=WorkflowDispatchTrigger(comment="dispatch note"))
    assert to_data(on) == {"workflow_dispatch": None}
    assert to_data(on, comments=True) == {
        "workflow_dispatch": CommentNode(None, comment="dispatch note")
    }


def test_present_null_fires_when_the_empty_model_carries_an_eol_comment():
    on = On(workflow_dispatch=WorkflowDispatchTrigger(eol_comment="dispatch note"))
    assert to_data(on) == {"workflow_dispatch": None}
    assert to_data(on, comments=True) == {
        "workflow_dispatch": CommentNode(None, eol_comment="dispatch note")
    }


def test_present_null_keeps_a_field_comment_on_the_nulled_key():
    """The already-working half: a ``Commented`` wrapper at the field position."""
    on = On(workflow_dispatch=with_comment(WorkflowDispatchTrigger(), "field note"))
    assert to_data(on) == {"workflow_dispatch": None}
    assert to_data(on, comments=True) == {
        "workflow_dispatch": CommentNode(None, comment="field note")
    }


def test_present_null_model_comment_survives_into_emitted_yaml():
    """The comment is the only content the user wrote; it must not vanish.

    Both ports dropped it: the comment was attached to the empty map, which
    ``present_null_when_empty`` then replaced with null, discarding the map and
    the comment with it.
    """
    wf = Workflow(
        name="CI",
        on=On(workflow_dispatch=WorkflowDispatchTrigger(comment="dispatch note")),
        jobs={},
    )
    assert "# dispatch note\n  workflow_dispatch:\n" in wf.to_yaml(header=None)


def test_non_model_raises_type_error():
    with pytest.raises(TypeError):
        to_data({"not": "a model"})  # type: ignore[arg-type]
    with pytest.raises(TypeError):
        to_data("just a string")  # type: ignore[arg-type]


def test_bare_step_run_dedented_by_default():
    # Parity with the ruamel recursion: a bare Step's run dedents wherever it is
    # encountered, not only inside a Document.
    data = to_data(Step(run="  echo one\n  echo two"))
    assert data["run"] == "echo one\necho two"


def test_to_data_and_to_yaml_agree_on_run_with_no_options():
    # The deliverable invariant (issue 13): a to_data / to_yaml pair called
    # with no options must never disagree about a Step's run. Both default
    # auto_dedent to True, so this must hold for any indented multi-line run.
    step = Step(name="Build", run="  echo building\n  make all")
    wf = Workflow(
        name="CI",
        jobs={"build": Job(runs_on="ubuntu-latest", steps=[step])},
    )
    yaml = YAML(typ="safe")
    parsed = yaml.load(io.StringIO(wf.to_yaml(header=None)))
    run_from_yaml = parsed["jobs"]["build"]["steps"][0]["run"]
    run_from_data = to_data(wf)["jobs"]["build"]["steps"][0]["run"]
    assert run_from_data == run_from_yaml == "echo building\nmake all"


def test_deep_structure_matches_emitted_yaml():
    # Deep structural cross-check (proposal 02): the parsed emitted YAML tree
    # must equal to_data's output for a RICH document, so the two duplicated
    # recursions cannot diverge on exclude/unwrap/present-null/dedent — not just
    # top-level ordering. Comments are dropped by the YAML parse, so to_data runs
    # with comments off; auto_dedent is left at its default, which now matches
    # ``to_yaml``'s default-on.
    wf = Workflow(
        name="CI",
        on=On(
            push=PushTrigger(branches=["main"]),
            workflow_dispatch=WorkflowDispatchTrigger(),  # present-null empty map
            extras={"merge_group": {}},  # extra on the alphabetical On spec
        ),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                needs=[],  # empty list: the shape a one-sided membership edit hides in
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
    assert to_data(wf) == parsed
