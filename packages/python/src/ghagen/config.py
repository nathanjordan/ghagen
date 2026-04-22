"""Project-level options loaded from .ghagen.yml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ghagen._yaml_config import load_yaml_config as _load_yaml


@dataclass
class GhagenOptions:
    """Options controlling ghagen behaviour.

    Loaded from the ``options:`` section in ``.ghagen.yml``.
    """

    auto_dedent: bool = True


def _parse_bool(value: Any, key: str, source: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f"{source}: [options].{key} must be a boolean, got {type(value).__name__}"
        )
    return value


def _extract_from_ghagen_yml(path: Path) -> GhagenOptions | None:
    data = _load_yaml(path)
    options = data.get("options")
    if options is None:
        return None
    if not isinstance(options, dict):
        raise ValueError(f"{path}: [options] must be a table")
    return GhagenOptions(
        auto_dedent=_parse_bool(
            options.get("auto_dedent", True), "auto_dedent", str(path)
        ),
    )


def load_options(cwd: Path) -> GhagenOptions:
    """Load project options from ``.ghagen.yml`` at the repository root.

    Falls back to default values when no config file is found or when the
    file does not contain an ``options:`` section.
    """
    ghagen_yml = cwd / ".ghagen.yml"

    if ghagen_yml.exists():
        result = _extract_from_ghagen_yml(ghagen_yml)
        if result is not None:
            return result

    return GhagenOptions()
