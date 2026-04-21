"""Tests for lint output formatters (human, JSON, GitHub annotations)."""

from __future__ import annotations

import json
from pathlib import Path

from ghagen.lint.output import format_github, format_human, format_json
from ghagen.lint.violation import Severity, SourceLocation, Violation


def _sample_violations() -> list[Violation]:
    return [
        Violation(
            rule_id="missing-permissions",
            severity=Severity.WARNING,
            message="Workflow 'ci' has no top-level permissions set.",
            location=SourceLocation(
                file=Path(".github/ghagen_workflows.py"),
                line=42,
                symbolic="ci.yml",
            ),
            hint="Add permissions=Permissions(contents='read').",
        ),
        Violation(
            rule_id="unpinned-actions",
            severity=Severity.ERROR,
            message="Step uses unpinned action 'actions/checkout@main'.",
            location=SourceLocation(
                file=Path(".github/ghagen_workflows.py"),
                line=78,
                symbolic="ci.yml → jobs.build → steps[0]",
            ),
            hint="Pin to a version tag or commit SHA.",
        ),
    ]


# -------- human format --------


def test_format_human_empty() -> None:
    output = format_human([])
    assert "no violations" in output.lower() or "0 violations" in output.lower()


def test_format_human_lists_violations() -> None:
    output = format_human(_sample_violations())
    assert "missing-permissions" in output
    assert "unpinned-actions" in output
    assert "warning" in output
    assert "error" in output
    assert "ghagen_workflows.py" in output
    assert "42" in output
    assert "78" in output
    assert "hint" in output.lower() or "Add permissions" in output


def test_format_human_shows_summary() -> None:
    output = format_human(_sample_violations())
    # Should mention counts somewhere
    assert "2" in output
    assert "1 error" in output or "errors: 1" in output.lower()


def test_format_human_omits_file_when_none() -> None:
    v = Violation(
        rule_id="x",
        severity=Severity.WARNING,
        message="m",
        location=SourceLocation(file=None, line=None, symbolic="ci.yml"),
    )
    output = format_human([v])
    # Should not crash, should still include symbolic path
    assert "ci.yml" in output


# -------- JSON format --------


def test_format_json_empty() -> None:
    output = format_json([])
    data = json.loads(output)
    assert data == {
        "violations": [],
        "summary": {"errors": 0, "warnings": 0},
    }


def test_format_json_structure() -> None:
    output = format_json(_sample_violations())
    data = json.loads(output)
    assert "violations" in data
    assert "summary" in data
    assert data["summary"] == {"errors": 1, "warnings": 1}
    assert len(data["violations"]) == 2

    first = data["violations"][0]
    assert first["rule_id"] == "missing-permissions"
    assert first["severity"] == "warning"
    assert first["message"]
    assert first["hint"]
    assert first["location"]["file"].endswith("ghagen_workflows.py")
    assert first["location"]["line"] == 42
    assert first["location"]["symbolic"] == "ci.yml"


def test_format_json_handles_none_file() -> None:
    v = Violation(
        rule_id="x",
        severity=Severity.WARNING,
        message="m",
        location=SourceLocation(file=None, line=None, symbolic="ci.yml"),
    )
    output = format_json([v])
    data = json.loads(output)
    loc = data["violations"][0]["location"]
    assert loc["file"] is None
    assert loc["line"] is None


# -------- GitHub annotations format --------


def test_format_github_empty() -> None:
    assert format_github([]) == ""


def test_format_github_annotation_commands() -> None:
    output = format_github(_sample_violations())
    lines = [line for line in output.split("\n") if line]
    assert len(lines) == 2
    assert lines[0].startswith("::warning ")
    assert "file=.github/ghagen_workflows.py" in lines[0]
    assert "line=42" in lines[0]
    assert "title=missing-permissions" in lines[0]
    assert lines[0].endswith("::Workflow 'ci' has no top-level permissions set.")

    assert lines[1].startswith("::error ")
    assert "title=unpinned-actions" in lines[1]


def test_format_github_skips_annotation_without_file() -> None:
    """GitHub annotations without a file still work (no file= prefix)."""
    v = Violation(
        rule_id="x",
        severity=Severity.WARNING,
        message="m",
        location=SourceLocation(file=None, line=None, symbolic="ci.yml"),
    )
    output = format_github([v])
    # Should still produce a line, just without file= / line=
    assert "::warning" in output
    assert "file=" not in output


def test_format_github_escapes_special_characters() -> None:
    """Messages containing newlines / commas / colons must be escaped
    per GitHub's workflow-command encoding."""
    v = Violation(
        rule_id="x",
        severity=Severity.WARNING,
        message="bad: things, happened\nnewline here",
        location=SourceLocation(file=Path("a.py"), line=1, symbolic="ci.yml"),
    )
    output = format_github([v])
    # Must be a single line (newline in message escaped)
    assert output.count("\n") == 1  # trailing newline only
    # GitHub encodes newline as %0A
    assert "%0A" in output
