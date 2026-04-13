"""Tests for the `missing-timeout` lint rule."""

from __future__ import annotations

from ghagen import Job, Step, Workflow
from ghagen.lint.config import LintConfig
from ghagen.lint.rules._base import RuleContext
from ghagen.lint.rules.missing_timeout import check_missing_timeout
from ghagen.lint.violation import Severity


def _ctx() -> RuleContext:
    return RuleContext(workflow_key="ci", config=LintConfig())


def test_rule_metadata() -> None:
    meta = check_missing_timeout.meta
    assert meta.id == "missing-timeout"
    assert meta.default_severity == Severity.WARNING


def test_flags_job_without_timeout() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(runs_on="ubuntu-latest", steps=[Step(run="echo hi")]),
        },
    )
    violations = list(check_missing_timeout(wf, _ctx()))
    assert len(violations) == 1
    assert "build" in violations[0].message


def test_accepts_job_with_timeout() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(run="echo hi")],
                timeout_minutes=10,
            ),
        },
    )
    assert list(check_missing_timeout(wf, _ctx())) == []


def test_skips_reusable_workflow_jobs() -> None:
    """A job that uses a reusable workflow has its own timeout via `uses`.
    It should NOT be flagged for missing timeout_minutes."""
    wf = Workflow(
        name="ci",
        jobs={
            "release": Job(uses="./.github/workflows/release.yml"),
        },
    )
    assert list(check_missing_timeout(wf, _ctx())) == []


def test_flags_multiple_jobs_independently() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "a": Job(runs_on="ubuntu-latest", steps=[Step(run="a")]),
            "b": Job(
                runs_on="ubuntu-latest",
                steps=[Step(run="b")],
                timeout_minutes=15,
            ),
            "c": Job(runs_on="ubuntu-latest", steps=[Step(run="c")]),
        },
    )
    violations = list(check_missing_timeout(wf, _ctx()))
    assert len(violations) == 2
    flagged = {v.message for v in violations}
    assert any("'a'" in m for m in flagged)
    assert any("'c'" in m for m in flagged)


def test_symbolic_location_includes_job_id() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "deploy": Job(runs_on="ubuntu-latest", steps=[Step(run="hi")]),
        },
    )
    violations = list(check_missing_timeout(wf, _ctx()))
    assert len(violations) == 1
    assert "deploy" in violations[0].location.symbolic
