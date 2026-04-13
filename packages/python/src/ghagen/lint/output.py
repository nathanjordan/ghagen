"""Output formatters for lint violations.

Three formats are supported:

- ``format_human``   — pretty terminal output for humans
- ``format_json``    — machine-readable JSON for CI and tooling
- ``format_github``  — GitHub Actions workflow-command annotations
"""

from __future__ import annotations

import json
from collections.abc import Iterable

from ghagen.lint.violation import Severity, Violation


def _counts(violations: Iterable[Violation]) -> tuple[int, int]:
    errors = sum(1 for v in violations if v.severity == Severity.ERROR)
    warnings = sum(1 for v in violations if v.severity == Severity.WARNING)
    return errors, warnings


# ---------------------------------------------------------------- human


def format_human(violations: list[Violation]) -> str:
    """Render violations as human-readable terminal output."""
    if not violations:
        return "No violations found.\n"

    lines: list[str] = []
    for v in violations:
        loc = v.location
        if loc.file is not None and loc.line is not None:
            prefix = f"{loc.file}:{loc.line}"
        elif loc.file is not None:
            prefix = str(loc.file)
        else:
            prefix = "<unknown>"

        lines.append(f"{prefix}: {v.severity}[{v.rule_id}]")
        lines.append(f"  {v.message}")
        lines.append(f"  Symbolic path: {loc.symbolic}")
        if v.hint:
            lines.append(f"  hint: {v.hint}")
        lines.append("")  # blank line between entries

    errors, warnings = _counts(violations)
    total = errors + warnings
    summary = (
        f"Found {total} violation{'s' if total != 1 else ''} "
        f"({errors} error{'s' if errors != 1 else ''}, "
        f"{warnings} warning{'s' if warnings != 1 else ''})."
    )
    lines.append(summary)
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------- json


def _violation_to_dict(v: Violation) -> dict:
    loc = v.location
    return {
        "rule_id": v.rule_id,
        "severity": v.severity.value,
        "message": v.message,
        "location": {
            "file": str(loc.file) if loc.file is not None else None,
            "line": loc.line,
            "symbolic": loc.symbolic,
        },
        "hint": v.hint,
    }


def format_json(violations: list[Violation]) -> str:
    """Render violations as a JSON document."""
    errors, warnings = _counts(violations)
    payload = {
        "violations": [_violation_to_dict(v) for v in violations],
        "summary": {"errors": errors, "warnings": warnings},
    }
    return json.dumps(payload, indent=2)


# ---------------------------------------------------------------- github


def _escape_gh_message(msg: str) -> str:
    """Escape a message for GitHub workflow-command encoding.

    See: https://docs.github.com/en/actions/using-workflows/workflow-commands-for-github-actions
    """
    return (
        msg.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
    )


def _escape_gh_property(value: str) -> str:
    """Escape a property value (file=, title=, etc.) for GH commands."""
    return (
        value.replace("%", "%25")
        .replace("\r", "%0D")
        .replace("\n", "%0A")
        .replace(":", "%3A")
        .replace(",", "%2C")
    )


def format_github(violations: list[Violation]) -> str:
    """Render violations as GitHub Actions workflow-command annotations."""
    if not violations:
        return ""

    lines: list[str] = []
    for v in violations:
        level = "error" if v.severity == Severity.ERROR else "warning"
        props: list[str] = []
        if v.location.file is not None:
            props.append(f"file={_escape_gh_property(str(v.location.file))}")
            if v.location.line is not None:
                props.append(f"line={v.location.line}")
        props.append(f"title={_escape_gh_property(v.rule_id)}")
        props_str = ",".join(props)
        lines.append(f"::{level} {props_str}::{_escape_gh_message(v.message)}")

    return "\n".join(lines) + "\n"
