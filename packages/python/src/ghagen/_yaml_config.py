"""Shared YAML loading utility."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError


def load_yaml_config(path: Path) -> dict[str, Any]:
    """Read and parse a YAML file, raising ``ValueError`` on parse errors."""
    yaml = YAML()
    try:
        with path.open() as f:
            data = yaml.load(f)
    except YAMLError as exc:
        raise ValueError(f"{path}: failed to parse YAML: {exc}") from exc
    if data is None:
        return {}
    if not isinstance(data, dict):
        raise ValueError(f"{path}: expected a YAML mapping at top level")
    return dict(data)
