"""Tests for the `missing-permissions` lint rule."""

from __future__ import annotations

from ghagen import Job, Permissions, Step, Workflow
from ghagen.lint.config import LintConfig
from ghagen.lint.rules._base import RuleContext
from ghagen.lint.rules.missing_permissions import check_missing_permissions
from ghagen.lint.violation import Severity


def _ctx() -> RuleContext:
    return RuleContext(workflow_key="ci", config=LintConfig())


def _minimal_job() -> Job:
    return Job(runs_on="ubuntu-latest", steps=[Step(run="echo hi")])


def test_rule_metadata() -> None:
    meta = check_missing_permissions.meta
    assert meta.id == "missing-permissions"
    assert meta.default_severity == Severity.WARNING
    assert "permission" in meta.description.lower()


def test_flags_workflow_with_no_permissions() -> None:
    wf = Workflow(name="ci", jobs={"build": _minimal_job()})
    violations = list(check_missing_permissions(wf, _ctx()))
    assert len(violations) == 1
    v = violations[0]
    assert v.rule_id == "missing-permissions"
    assert v.severity == Severity.WARNING
    assert v.location.symbolic == "ci.yml"
    assert v.hint is not None


def test_accepts_top_level_permissions() -> None:
    wf = Workflow(
        name="ci",
        permissions=Permissions(contents="read"),
        jobs={"build": _minimal_job()},
    )
    assert list(check_missing_permissions(wf, _ctx())) == []


def test_accepts_string_shorthand_permissions() -> None:
    wf = Workflow(name="ci", permissions="read-all", jobs={"build": _minimal_job()})
    assert list(check_missing_permissions(wf, _ctx())) == []


def test_accepts_all_jobs_having_permissions() -> None:
    """If every job sets its own permissions, top-level can be omitted."""
    job = Job(
        runs_on="ubuntu-latest",
        permissions=Permissions(contents="read"),
        steps=[Step(run="echo hi")],
    )
    wf = Workflow(name="ci", jobs={"build": job})
    assert list(check_missing_permissions(wf, _ctx())) == []


def test_flags_when_only_some_jobs_have_permissions() -> None:
    """If one job has permissions but another doesn't, still flag the workflow."""
    locked = Job(
        runs_on="ubuntu-latest",
        permissions=Permissions(contents="read"),
        steps=[Step(run="echo hi")],
    )
    unlocked = _minimal_job()
    wf = Workflow(name="ci", jobs={"build": locked, "deploy": unlocked})
    violations = list(check_missing_permissions(wf, _ctx()))
    assert len(violations) == 1


def test_respects_severity_override() -> None:
    wf = Workflow(name="ci", jobs={"build": _minimal_job()})
    ctx = RuleContext(
        workflow_key="ci",
        config=LintConfig(severity={"missing-permissions": Severity.ERROR}),
    )
    violations = list(check_missing_permissions(wf, ctx))
    assert len(violations) == 1
    assert violations[0].severity == Severity.ERROR
