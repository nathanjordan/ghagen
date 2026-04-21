"""Project-level options loaded from ghagen.toml or pyproject.toml."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ghagen._toml import load_toml as _load_toml


@dataclass
class GhagenOptions:
    """Options controlling ghagen behaviour.

    Loaded from ``[options]`` in ``.github/ghagen.toml`` or
    ``[tool.ghagen.options]`` in ``pyproject.toml``.
    """

    auto_dedent: bool = True


def _parse_bool(value: Any, key: str, source: str) -> bool:
    if not isinstance(value, bool):
        raise ValueError(
            f"{source}: [options].{key} must be a boolean, got {type(value).__name__}"
        )
    return value


def _extract_from_ghagen_toml(path: Path) -> GhagenOptions | None:
    data = _load_toml(path)
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


def _extract_from_pyproject(path: Path) -> GhagenOptions | None:
    data = _load_toml(path)
    tool = data.get("tool", {})
    if not isinstance(tool, dict):
        return None
    ghagen = tool.get("ghagen", {})
    if not isinstance(ghagen, dict):
        return None
    options = ghagen.get("options")
    if options is None:
        return None
    if not isinstance(options, dict):
        raise ValueError(f"{path}: [tool.ghagen.options] must be a table")
    return GhagenOptions(
        auto_dedent=_parse_bool(
            options.get("auto_dedent", True), "auto_dedent", str(path)
        ),
    )


def load_options(cwd: Path) -> GhagenOptions:
    """Load project options from standard config file locations.

    Precedence (highest wins):

    1. ``.github/ghagen.toml`` ``[options]`` section
    2. ``pyproject.toml`` ``[tool.ghagen.options]`` section
    3. Defaults
    """
    ghagen_toml = cwd / ".github" / "ghagen.toml"
    pyproject = cwd / "pyproject.toml"

    if ghagen_toml.exists():
        result = _extract_from_ghagen_toml(ghagen_toml)
        if result is not None:
            return result

    if pyproject.exists():
        result = _extract_from_pyproject(pyproject)
        if result is not None:
            return result

    return GhagenOptions()
