"""Path utilities for locating the ghagen project root."""

from __future__ import annotations

from pathlib import Path

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
