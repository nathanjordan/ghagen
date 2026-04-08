"""Tests for the @rule decorator, RuleMeta, and RuleContext."""

from __future__ import annotations

from pathlib import Path

from ghagen import Step, Workflow
from ghagen.lint.config import LintConfig
from ghagen.lint.rules._base import RuleContext, RuleMeta, rule
from ghagen.lint.violation import Severity, SourceLocation, Violation


def test_rule_decorator_attaches_metadata() -> None:
    @rule(id="test-rule", severity=Severity.WARNING, description="a test rule")
    def my_rule(wf: Workflow, ctx: RuleContext):  # pyright: ignore
        return []

    assert hasattr(my_rule, "meta")
    meta = my_rule.meta
    assert isinstance(meta, RuleMeta)
    assert meta.id == "test-rule"
    assert meta.description == "a test rule"
    assert meta.default_severity == Severity.WARNING


def test_rule_context_loc_from_model_with_location() -> None:
    """RuleContext.loc() builds a SourceLocation from a model's
    _source_location and a symbolic path string."""
    step = Step(run="echo hi")
    ctx = RuleContext(workflow_key="ci", config=LintConfig())

    loc = ctx.loc(step, "ci.yml → jobs.build → steps[0]")

    assert isinstance(loc, SourceLocation)
    assert loc.symbolic == "ci.yml → jobs.build → steps[0]"
    assert loc.file is not None
    assert str(loc.file).endswith("test_rule_base.py")
    assert loc.line is not None


def test_rule_context_loc_falls_back_when_no_source() -> None:
    """If a model has no captured source location, loc() still returns a
    valid SourceLocation with symbolic only."""
    step = Step(run="echo hi")
    # Simulate unavailable source
    step._source_location = None

    ctx = RuleContext(workflow_key="ci", config=LintConfig())
    loc = ctx.loc(step, "ci.yml → jobs.build → steps[0]")

    assert loc.file is None
    assert loc.line is None
    assert loc.symbolic == "ci.yml → jobs.build → steps[0]"


def test_rule_function_returns_violations() -> None:
    """A rule function can yield Violation instances normally."""

    @rule(
        id="demo",
        severity=Severity.ERROR,
        description="demo",
    )
    def demo_rule(wf: Workflow, ctx: RuleContext):
        yield Violation(
            rule_id="demo",
            severity=ctx.config.severity.get("demo", Severity.ERROR),
            message="boom",
            location=SourceLocation(file=None, line=None, symbolic="x"),
        )

    wf = Workflow(name="x", jobs={})
    ctx = RuleContext(workflow_key="x", config=LintConfig())
    violations = list(demo_rule(wf, ctx))
    assert len(violations) == 1
    assert violations[0].message == "boom"


def test_rule_context_resolves_path_from_models(tmp_path: Path) -> None:
    """loc() should coerce the file path to a Path instance."""
    step = Step(run="echo hi")
    ctx = RuleContext(workflow_key="ci", config=LintConfig())
    loc = ctx.loc(step, "symbolic")
    assert isinstance(loc.file, Path)
