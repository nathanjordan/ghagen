"""Common types shared across models."""

from __future__ import annotations

from enum import StrEnum


class ShellType(StrEnum):
    """Supported shell types for run steps."""

    BASH = "bash"
    PWSH = "pwsh"
    PYTHON = "python"
    SH = "sh"
    CMD = "cmd"


class PermissionLevel(StrEnum):
    """Permission access levels."""

    READ = "read"
    WRITE = "write"
    NONE = "none"


class ExpressionStr(str):
    """A string that represents a GitHub Actions expression (${{ ... }}).

    This is a regular string subclass — use it as a marker type to indicate
    that a value is a GHA expression rather than a literal string.
    """

    @classmethod
    def wrap(cls, expr: str) -> ExpressionStr:
        """Wrap a bare expression in ${{ }} if not already wrapped."""
        if expr.startswith("${{") and expr.endswith("}}"):
            return cls(expr)
        return cls(f"${{{{ {expr} }}}}")
