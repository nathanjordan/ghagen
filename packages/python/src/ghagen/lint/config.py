"""Lint configuration loaded from .ghagen.yml."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from ghagen._yaml_config import load_yaml_config as _load_yaml
from ghagen.lint.violation import Severity


@dataclass
class LintConfig:
    """Configuration controlling which rules run at what severity."""

    disable: set[str] = field(default_factory=set)
    severity: dict[str, Severity] = field(default_factory=dict)


def _parse_severity_map(raw: Any, source: str) -> dict[str, Severity]:
    """Coerce a raw YAML severity mapping into a ``dict[str, Severity]``."""
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


def _extract_from_ghagen_yml(path: Path) -> LintConfig | None:
    """Return LintConfig from .ghagen.yml, or None if the lint section is absent."""
    data = _load_yaml(path)
    lint = data.get("lint")
    if lint is None:
        return None
    if not isinstance(lint, dict):
        raise ValueError(f"{path}: 'lint' must be a mapping")
    return LintConfig(
        disable=_parse_disable(lint.get("disable"), str(path)),
        severity=_parse_severity_map(lint.get("severity"), str(path)),
    )


def load_config(
    cwd: Path,
    cli_disable: Iterable[str] = (),
) -> tuple[LintConfig, list[str]]:
    """Load lint config from ``.ghagen.yml`` and merge CLI overrides.

    Returns:
        A tuple of (``LintConfig``, warnings) where warnings is a list
        of human-readable strings (always empty; kept for API compat).
    """
    warnings: list[str] = []

    ghagen_yml = cwd / ".ghagen.yml"

    if ghagen_yml.exists():
        chosen = _extract_from_ghagen_yml(ghagen_yml) or LintConfig()
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
