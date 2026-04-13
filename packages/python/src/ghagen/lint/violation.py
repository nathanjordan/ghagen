"""Violation, Severity, and SourceLocation dataclasses for ghagen lint."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path


class Severity(StrEnum):
    """Severity level for a lint violation."""

    ERROR = "error"
    WARNING = "warning"


@dataclass(frozen=True, slots=True)
class SourceLocation:
    """Where in the user's code a violation was found.

    ``file`` and ``line`` point at the Python source that constructed
    the offending model (captured via frame inspection). ``symbolic``
    is always set and describes the logical path within the workflow
    tree (e.g. ``"ci.yml → jobs.build → steps[2]"``).
    """

    file: Path | None
    line: int | None
    symbolic: str


@dataclass(frozen=True, slots=True)
class Violation:
    """A single lint violation produced by a rule."""

    rule_id: str
    severity: Severity
    message: str
    location: SourceLocation
    hint: str | None = None
