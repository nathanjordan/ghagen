"""Project configuration: root discovery, YAML loading, and options.

This module unifies three concerns that used to live apart:

* **Root discovery** — :func:`find_app_root` walks upward looking for the
  ``.ghagen.yml`` marker. It is the *single* root locator used by both
  :func:`load_options` and the header's ``{source_file}`` resolution.
* **YAML loading** — :func:`load_yaml_config` reads and validates a YAML
  mapping file.
* **Options** — :class:`GhagenOptions` / :func:`load_options` read the
  ``options:`` section of ``.ghagen.yml``.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from ruamel.yaml import YAML, YAMLError

#: Canonical marker file: its presence identifies the ghagen project root.
GHAGEN_YML_MARKER = Path(".ghagen.yml")


def find_app_root(start: Path | None = None) -> Path | None:
    """Walk upward from *start* looking for ``.ghagen.yml``.

    Returns the directory containing ``.ghagen.yml`` if found,
    else ``None``. When *start* is ``None``, walks from ``Path.cwd()``.
    When *start* refers to a file, the search begins at the file's
    parent directory.

    Args:
        start: The path to begin searching from. May be a directory or
            a file. Defaults to the current working directory.

    Returns:
        The resolved directory containing ``.ghagen.yml``, or
        ``None`` if no ancestor contains the marker.
    """
    base = (start or Path.cwd()).resolve()
    if base.is_file():
        base = base.parent

    for parent in [base, *base.parents]:
        if (parent / GHAGEN_YML_MARKER).is_file():
            return parent
    return None


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


@dataclass
class GhagenOptions:
    """Options controlling ghagen behaviour.

    Loaded from the ``options:`` section in ``.ghagen.yml``.
    """

    auto_dedent: bool = True


def load_options(start: Path | None = None) -> GhagenOptions:
    """Load project options from ``.ghagen.yml`` at the repository root.

    The config file is located via :func:`find_app_root` (an ancestor
    walk from *start*), the same discovery used for the header's
    ``{source_file}`` resolution. Falls back to default values when no
    config file is found or when the file does not contain an
    ``options:`` section.

    Args:
        start: Directory (or file) to begin the ancestor walk from.
            Defaults to the current working directory.
    """
    root = find_app_root(start)
    if root is None:
        return GhagenOptions()

    path = root / GHAGEN_YML_MARKER
    options = load_yaml_config(path).get("options")
    if options is None:
        return GhagenOptions()
    if not isinstance(options, dict):
        raise ValueError(f"{path}: [options] must be a table")

    auto_dedent = options.get("auto_dedent", True)
    if not isinstance(auto_dedent, bool):
        raise ValueError(
            f"{path}: [options].auto_dedent must be a boolean, "
            f"got {type(auto_dedent).__name__}"
        )

    return GhagenOptions(auto_dedent=auto_dedent)
