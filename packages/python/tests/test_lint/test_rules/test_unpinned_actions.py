"""Tests for the `unpinned-actions` lint rule."""

from __future__ import annotations

from ghagen import Job, Step, Workflow
from ghagen.lint.config import LintConfig
from ghagen.lint.rules._base import RuleContext
from ghagen.lint.rules.unpinned_actions import check_unpinned_actions
from ghagen.lint.violation import Severity


def _ctx() -> RuleContext:
    return RuleContext(workflow_key="ci", config=LintConfig())


def _wf_with_step(step: Step) -> Workflow:
    return Workflow(
        name="ci",
        jobs={"build": Job(runs_on="ubuntu-latest", steps=[step])},
    )


def test_rule_metadata() -> None:
    meta = check_unpinned_actions.meta
    assert meta.id == "unpinned-actions"
    assert meta.default_severity == Severity.WARNING


def test_flags_action_pinned_to_main() -> None:
    wf = _wf_with_step(Step(uses="actions/checkout@main"))
    violations = list(check_unpinned_actions(wf, _ctx()))
    assert len(violations) == 1
    assert "main" in violations[0].message


def test_flags_action_pinned_to_master() -> None:
    wf = _wf_with_step(Step(uses="actions/checkout@master"))
    assert len(list(check_unpinned_actions(wf, _ctx()))) == 1


def test_flags_action_pinned_to_latest() -> None:
    wf = _wf_with_step(Step(uses="actions/checkout@latest"))
    assert len(list(check_unpinned_actions(wf, _ctx()))) == 1


def test_flags_action_with_no_ref() -> None:
    wf = _wf_with_step(Step(uses="actions/checkout"))
    assert len(list(check_unpinned_actions(wf, _ctx()))) == 1


def test_accepts_major_version_tag() -> None:
    wf = _wf_with_step(Step(uses="actions/checkout@v4"))
    assert list(check_unpinned_actions(wf, _ctx())) == []


def test_accepts_semver_tag() -> None:
    wf = _wf_with_step(Step(uses="actions/checkout@v4.1.2"))
    assert list(check_unpinned_actions(wf, _ctx())) == []


def test_accepts_commit_sha() -> None:
    wf = _wf_with_step(
        Step(uses="actions/checkout@b4ffde65f46336ab88eb53be808477a3936bae11")
    )
    assert list(check_unpinned_actions(wf, _ctx())) == []


def test_skips_local_action_reference() -> None:
    """./ references are local, not pinnable, so skip them."""
    wf = _wf_with_step(Step(uses="./.github/actions/my-action"))
    assert list(check_unpinned_actions(wf, _ctx())) == []


def test_skips_docker_action() -> None:
    """docker:// references are version-pinned via image tag, skip."""
    wf = _wf_with_step(Step(uses="docker://alpine:3.18"))
    assert list(check_unpinned_actions(wf, _ctx())) == []


def test_skips_steps_with_no_uses() -> None:
    wf = _wf_with_step(Step(run="echo hi"))
    assert list(check_unpinned_actions(wf, _ctx())) == []


def test_flags_multiple_steps_independently() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@main"),
                    Step(uses="actions/setup-python@v5"),  # ok
                    Step(uses="astral-sh/setup-uv@master"),  # bad
                ],
            )
        },
    )
    violations = list(check_unpinned_actions(wf, _ctx()))
    assert len(violations) == 2


def test_symbolic_location_includes_job_and_step_index() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(run="setup"),
                    Step(uses="actions/checkout@main"),
                ],
            )
        },
    )
    violations = list(check_unpinned_actions(wf, _ctx()))
    assert len(violations) == 1
    assert "build" in violations[0].location.symbolic
    assert "steps[1]" in violations[0].location.symbolic
