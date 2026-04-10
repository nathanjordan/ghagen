"""Lint configuration loaded from .github/ghagen.toml or pyproject.toml."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ghagen._toml import load_toml as _load_toml
from ghagen.lint.violation import Severity


@dataclass
class LintConfig:
    """Configuration controlling which rules run at what severity."""

    disable: set[str] = field(default_factory=set)
    severity: dict[str, Severity] = field(default_factory=dict)


def _parse_severity_map(raw: Any, source: str) -> dict[str, Severity]:
    """Coerce a raw TOML severity mapping into a ``dict[str, Severity]``."""
    if raw is None:
        return {}
    if not isinstance(raw, dict):
        raise ValueError(
            f"{source}: [lint.severity] must be a table, got {type(raw).__name__}"
        )
    result: dict[str, Severity] = {}
    for rule_id, value in raw.items():
        if not isinstance(value, str):
            raise ValueError(
                f"{source}: severity for '{rule_id}' must be a string, "
                f"got {type(value).__name__}"
            )
        try:
            result[rule_id] = Severity(value)
        except ValueError as exc:
            valid = ", ".join(s.value for s in Severity)
            raise ValueError(
                f"{source}: invalid severity '{value}' for rule '{rule_id}' "
                f"(valid values: {valid})"
            ) from exc
    return result


def _parse_disable(raw: Any, source: str) -> set[str]:
    if raw is None:
        return set()
    if not isinstance(raw, list):
        raise ValueError(
            f"{source}: [lint].disable must be a list, got {type(raw).__name__}"
        )
    for item in raw:
        if not isinstance(item, str):
            raise ValueError(
                f"{source}: [lint].disable entries must be strings, "
                f"got {type(item).__name__}"
            )
    return set(raw)


def _extract_from_ghagen_toml(path: Path) -> LintConfig:
    data = _load_toml(path)
    lint_section = data.get("lint", {})
    if not isinstance(lint_section, dict):
        raise ValueError(f"{path}: [lint] must be a table")
    return LintConfig(
        disable=_parse_disable(lint_section.get("disable"), str(path)),
        severity=_parse_severity_map(lint_section.get("severity"), str(path)),
    )


def _extract_from_pyproject(path: Path) -> LintConfig | None:
    """Return LintConfig from pyproject.toml, or None if the section is absent."""
    data = _load_toml(path)
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return None
    ghagen = tool.get("ghagen", {})
    if not isinstance(ghagen, dict):
        return None
    lint = ghagen.get("lint")
    if lint is None:
        return None
    if not isinstance(lint, dict):
        raise ValueError(f"{path}: [tool.ghagen.lint] must be a table")
    return LintConfig(
        disable=_parse_disable(lint.get("disable"), str(path)),
        severity=_parse_severity_map(lint.get("severity"), str(path)),
    )


def load_config(
    cwd: Path,
    cli_disable: Iterable[str] = (),
) -> tuple[LintConfig, list[str]]:
    """Load lint config from standard locations and merge CLI overrides.

    Precedence (highest wins):

    1. CLI flags (``cli_disable``) — unioned into the final disable set
    2. ``.github/ghagen.toml`` [lint] section
    3. ``pyproject.toml`` [tool.ghagen.lint] section
    4. Defaults (empty)

    When both ``.github/ghagen.toml`` and ``pyproject.toml`` provide a
    lint config, the former wins and a warning is returned describing
    which was used.

    Returns:
        A tuple of (``LintConfig``, warnings) where warnings is a list
        of human-readable strings to print to stderr.
    """
    warnings: list[str] = []

    ghagen_toml = cwd / ".github" / "ghagen.toml"
    pyproject = cwd / "pyproject.toml"

    ghagen_config: LintConfig | None = None
    pyproject_config: LintConfig | None = None

    if ghagen_toml.exists():
        ghagen_config = _extract_from_ghagen_toml(ghagen_toml)

    if pyproject.exists():
        pyproject_config = _extract_from_pyproject(pyproject)

    # Determine winner and emit multi-source warning if needed
    if ghagen_config is not None and pyproject_config is not None:
        warnings.append(
            "lint config found in multiple locations:\n"
            f"  - {ghagen_toml} (used)\n"
            f"  - {pyproject} [tool.ghagen.lint] (ignored)\n"
            "Remove one to silence this warning."
        )
        chosen = ghagen_config
    elif ghagen_config is not None:
        chosen = ghagen_config
    elif pyproject_config is not None:
        chosen = pyproject_config
    else:
        chosen = LintConfig()

    # Union CLI disables
    cli_set = set(cli_disable)
    if cli_set:
        chosen = LintConfig(
            disable=chosen.disable | cli_set,
            severity=chosen.severity,
        )

    return chosen, warnings
