"""Tests for the Violation / Severity / SourceLocation dataclasses."""

from __future__ import annotations

from pathlib import Path

import pytest

from ghagen.lint.violation import Severity, SourceLocation, Violation


def test_severity_values() -> None:
    assert Severity.ERROR == "error"
    assert Severity.WARNING == "warning"


def test_source_location_with_file_and_line() -> None:
    loc = SourceLocation(
        file=Path("ghagen_workflows.py"),
        line=42,
        symbolic="ci.yml",
    )
    assert loc.file == Path("ghagen_workflows.py")
    assert loc.line == 42
    assert loc.symbolic == "ci.yml"


def test_source_location_without_file() -> None:
    """A SourceLocation can have no file/line (e.g. fallback case)."""
    loc = SourceLocation(file=None, line=None, symbolic="ci.yml → jobs.build")
    assert loc.file is None
    assert loc.line is None
    assert loc.symbolic == "ci.yml → jobs.build"


def test_violation_construction() -> None:
    loc = SourceLocation(file=Path("x.py"), line=10, symbolic="ci.yml")
    v = Violation(
        rule_id="missing-permissions",
        severity=Severity.WARNING,
        message="No permissions set.",
        location=loc,
        hint="Add permissions=...",
    )
    assert v.rule_id == "missing-permissions"
    assert v.severity == Severity.WARNING
    assert v.message == "No permissions set."
    assert v.location == loc
    assert v.hint == "Add permissions=..."


def test_violation_hint_defaults_to_none() -> None:
    loc = SourceLocation(file=None, line=None, symbolic="ci.yml")
    v = Violation(
        rule_id="x",
        severity=Severity.ERROR,
        message="m",
        location=loc,
    )
    assert v.hint is None


def test_violation_is_frozen() -> None:
    loc = SourceLocation(file=None, line=None, symbolic="ci.yml")
    v = Violation(
        rule_id="x",
        severity=Severity.ERROR,
        message="m",
        location=loc,
    )
    with pytest.raises(AttributeError):
        v.rule_id = "y"  # type: ignore[misc]
