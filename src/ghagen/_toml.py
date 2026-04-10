"""Shared TOML loading utility."""

from __future__ import annotations

import tomllib
from pathlib import Path
from typing import Any


def load_toml(path: Path) -> dict[str, Any]:
    """Read and parse a TOML file, raising ``ValueError`` on parse errors."""
    try:
        with path.open("rb") as f:
            return tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        raise ValueError(f"{path}: failed to parse TOML: {exc}") from exc
