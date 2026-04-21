"""Tests for the LintEngine / run_lint() top-level entry point."""

from __future__ import annotations

from collections.abc import Iterable

from ghagen import App, Job, Permissions, Step, Workflow
from ghagen.lint.config import LintConfig
from ghagen.lint.engine import run_lint
from ghagen.lint.rules._base import RuleContext, rule
from ghagen.lint.violation import Severity, SourceLocation, Violation


def _minimal_clean_workflow() -> Workflow:
    """A workflow that passes all three built-in rules."""
    return Workflow(
        name="clean",
        permissions=Permissions(contents="read"),
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                timeout_minutes=10,
                steps=[Step(uses="actions/checkout@v4")],
            ),
        },
    )


def _violating_workflow() -> Workflow:
    """A workflow that triggers all three built-in rules."""
    return Workflow(
        name="bad",
        jobs={
            "build": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses="actions/checkout@main")],
            ),
        },
    )


def test_run_lint_on_clean_workflow_returns_empty() -> None:
    app = App()
    app.add_workflow(_minimal_clean_workflow(), "ci.yml")
    violations = run_lint(app, LintConfig())
    assert violations == []


def test_run_lint_on_violating_workflow_finds_all_three_rules() -> None:
    app = App()
    app.add_workflow(_violating_workflow(), "ci.yml")
    violations = run_lint(app, LintConfig())
    ids = {v.rule_id for v in violations}
    assert "missing-permissions" in ids
    assert "unpinned-actions" in ids
    assert "missing-timeout" in ids


def test_run_lint_uses_file_stem_as_workflow_key() -> None:
    """The symbolic path should use the filename stem as the workflow key."""
    app = App()
    app.add_workflow(_violating_workflow(), "release.yml")
    violations = run_lint(app, LintConfig())
    assert violations, "expected at least one violation"
    assert all(v.location.symbolic.startswith("release") for v in violations)


def test_run_lint_skips_disabled_rules() -> None:
    app = App()
    app.add_workflow(_violating_workflow(), "ci.yml")
    config = LintConfig(disable={"missing-permissions", "unpinned-actions"})
    violations = run_lint(app, config)
    ids = {v.rule_id for v in violations}
    assert ids == {"missing-timeout"}


def test_run_lint_applies_severity_overrides() -> None:
    app = App()
    app.add_workflow(_violating_workflow(), "ci.yml")
    config = LintConfig(severity={"missing-timeout": Severity.ERROR})
    violations = run_lint(app, config)
    timeout_v = next(v for v in violations if v.rule_id == "missing-timeout")
    assert timeout_v.severity == Severity.ERROR


def test_run_lint_ignores_actions_registered_on_app() -> None:
    """Actions (action.yml) are not workflows and shouldn't be linted by the
    workflow rules (at least not in v1)."""
    from ghagen import Action, CompositeRuns

    app = App()
    app.add_workflow(_violating_workflow(), "ci.yml")
    app.add_action(
        Action(
            name="my-action",
            description="a test",
            runs=CompositeRuns(steps=[Step(run="echo hi")]),
        )
    )
    violations = run_lint(app, LintConfig())
    # All violations should still come from the workflow, not the action
    assert all("ci" in v.location.symbolic for v in violations)


def test_run_lint_continues_when_a_rule_crashes(
    monkeypatch,  # type: ignore[no-untyped-def]
) -> None:
    """A crashing rule should not kill the whole lint run; other rules
    still execute."""
    from ghagen.lint import engine as engine_module

    @rule(id="crash", severity=Severity.ERROR, description="crashes")
    def crash_rule(wf: Workflow, ctx: RuleContext) -> Iterable[Violation]:
        raise RuntimeError("boom")
        yield  # pragma: no cover — unreachable but makes it a generator

    from ghagen.lint.rules.missing_timeout import check_missing_timeout

    monkeypatch.setattr(engine_module, "ALL_RULES", [crash_rule, check_missing_timeout])

    app = App()
    app.add_workflow(_violating_workflow(), "ci.yml")
    violations = run_lint(app, LintConfig())
    # The non-crashing rule should still have produced its violation
    assert any(v.rule_id == "missing-timeout" for v in violations)


def test_run_lint_returns_violations_with_populated_locations() -> None:
    app = App()
    app.add_workflow(_violating_workflow(), "ci.yml")
    violations = run_lint(app, LintConfig())
    for v in violations:
        assert isinstance(v.location, SourceLocation)
        assert v.location.symbolic
