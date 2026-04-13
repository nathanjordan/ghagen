"""Tests for the `duplicate-step-ids` lint rule."""

from __future__ import annotations

from ruamel.yaml.comments import CommentedMap

from ghagen import Job, Step, Workflow
from ghagen.lint.config import LintConfig
from ghagen.lint.rules._base import RuleContext
from ghagen.lint.rules.duplicate_step_ids import check_duplicate_step_ids
from ghagen.lint.violation import Severity


def _ctx(config: LintConfig | None = None) -> RuleContext:
    return RuleContext(workflow_key="ci", config=config or LintConfig())


def test_rule_metadata() -> None:
    meta = check_duplicate_step_ids.meta
    assert meta.id == "duplicate-step-ids"
    assert meta.default_severity == Severity.ERROR


def test_no_violations_when_ids_unique() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="checkout", uses="actions/checkout@v4"),
                    Step(id="build", run="make"),
                ],
            ),
        },
    )
    assert list(check_duplicate_step_ids(wf, _ctx())) == []


def test_no_violations_when_ids_absent() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(uses="actions/checkout@v4"),
                    Step(run="make"),
                    Step(run="make test"),
                ],
            ),
        },
    )
    assert list(check_duplicate_step_ids(wf, _ctx())) == []


def test_flags_simple_duplicate() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="foo", run="echo first"),
                    Step(id="foo", run="echo second"),
                ],
            ),
        },
    )
    violations = list(check_duplicate_step_ids(wf, _ctx()))
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "duplicate-step-ids"
    assert v.severity == Severity.ERROR
    assert "'foo'" in v.message
    assert "'build'" in v.message
    assert "steps[0]" in v.message  # references the first occurrence
    assert "steps[1]" in v.location.symbolic  # attributed to the duplicate


def test_flags_triple_duplicate_once_per_later_occurrence() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="foo", run="echo 1"),
                    Step(id="foo", run="echo 2"),
                    Step(id="foo", run="echo 3"),
                ],
            ),
        },
    )
    violations = list(check_duplicate_step_ids(wf, _ctx()))
    assert len(violations) == 2
    # Both violations should reference the first occurrence
    for v in violations:
        assert "steps[0]" in v.message
    # Attributed to the second and third occurrences respectively
    symbolics = {v.location.symbolic for v in violations}
    assert any("steps[1]" in s for s in symbolics)
    assert any("steps[2]" in s for s in symbolics)


def test_duplicate_across_jobs_is_ok() -> None:
    """Step ids are scoped per-job in GitHub Actions."""
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(id="foo", run="echo build")],
            ),
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(id="foo", run="echo test")],
            ),
        },
    )
    assert list(check_duplicate_step_ids(wf, _ctx())) == []


def test_mixed_ids_only_duplicates_flagged() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="foo", run="echo 1"),
                    Step(id="bar", run="echo 2"),
                    Step(id="foo", run="echo 3"),
                    Step(id="baz", run="echo 4"),
                ],
            ),
        },
    )
    violations = list(check_duplicate_step_ids(wf, _ctx()))
    assert len(violations) == 1
    assert "'foo'" in violations[0].message
    assert "steps[2]" in violations[0].location.symbolic


def test_handles_commentedmap_step_passthrough() -> None:
    """Raw CommentedMap escape-hatch steps should still be checked."""
    raw_step_a: CommentedMap = CommentedMap()
    raw_step_a["id"] = "shared"
    raw_step_a["run"] = "echo first"
    raw_step_b: CommentedMap = CommentedMap()
    raw_step_b["id"] = "shared"
    raw_step_b["run"] = "echo second"

    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[raw_step_a, raw_step_b],
            ),
        },
    )
    violations = list(check_duplicate_step_ids(wf, _ctx()))
    assert len(violations) == 1
    assert "'shared'" in violations[0].message


def test_handles_commentedmap_without_id() -> None:
    """A raw CommentedMap with no id key should not crash."""
    raw_step: CommentedMap = CommentedMap()
    raw_step["run"] = "echo hi"

    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[raw_step, Step(id="real", run="echo real")],
            ),
        },
    )
    assert list(check_duplicate_step_ids(wf, _ctx())) == []


def test_empty_string_id_is_ignored() -> None:
    """An empty-string id isn't a real id and shouldn't collide."""
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="", run="echo 1"),
                    Step(id="", run="echo 2"),
                ],
            ),
        },
    )
    assert list(check_duplicate_step_ids(wf, _ctx())) == []


def test_respects_severity_override() -> None:
    config = LintConfig(severity={"duplicate-step-ids": Severity.WARNING})
    wf = Workflow(
        name="ci",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="foo", run="echo 1"),
                    Step(id="foo", run="echo 2"),
                ],
            ),
        },
    )
    violations = list(check_duplicate_step_ids(wf, _ctx(config)))
    assert len(violations) == 1
    assert violations[0].severity == Severity.WARNING


def test_symbolic_location_includes_job_and_step_index() -> None:
    wf = Workflow(
        name="ci",
        jobs={
            "deploy": Job(
                runs_on="ubuntu-latest",
                steps=[
                    Step(id="foo", run="echo 1"),
                    Step(run="echo middle"),
                    Step(id="foo", run="echo 2"),
                ],
            ),
        },
    )
    violations = list(check_duplicate_step_ids(wf, _ctx()))
    assert len(violations) == 1
    loc = violations[0].location.symbolic
    assert "deploy" in loc
    assert "steps[2]" in loc
