"""Determine which Python source files contain each ``uses:`` ref string.

Distinguishes between user-authored files and ghagen internal files so that
the update command can propose edits only in user-controlled sources.
"""

from __future__ import annotations

import sys
import sysconfig
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ghagen.app import App


def _ghagen_package_root() -> Path:
    """Return the directory containing the ``ghagen`` package."""
    import ghagen

    return Path(ghagen.__file__).resolve().parent


def _is_user_file(path: Path, *, ghagen_root: Path) -> bool:
    """Return ``True`` if *path* is a user-authored file (not stdlib/site/ghagen)."""
    parts = path.parts

    # Exclude site-packages
    if "site-packages" in parts:
        return False

    # Exclude ghagen package files
    try:
        path.relative_to(ghagen_root)
        return False
    except ValueError:
        pass

    # Exclude stdlib files
    stdlib_paths = sysconfig.get_paths()
    for key in ("stdlib", "platstdlib", "purelib", "platlib"):
        stdlib_dir = stdlib_paths.get(key)
        if stdlib_dir:
            try:
                path.relative_to(stdlib_dir)
                return False
            except ValueError:
                pass

    return True


def track_user_files(app_loader: Callable[[], App]) -> set[Path]:
    """Discover which Python files were loaded as part of the user's config.

    Snapshots ``sys.modules`` before and after calling *app_loader*, then
    filters the newly imported modules to only user-authored files (excluding
    stdlib, site-packages, and the ghagen package itself).

    Args:
        app_loader: A zero-argument callable that imports the user's ghagen
            configuration and returns the :class:`~ghagen.app.App`.

    Returns:
        Set of absolute :class:`~pathlib.Path` objects for user source files.
    """
    before = set(sys.modules.keys())
    app_loader()
    after = set(sys.modules.keys())

    new_modules = after - before
    ghagen_root = _ghagen_package_root()

    user_files: set[Path] = set()
    for mod_name in new_modules:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", None)
        if mod_file is None:
            continue
        path = Path(mod_file).resolve()
        if _is_user_file(path, ghagen_root=ghagen_root):
            user_files.add(path)

    return user_files


def locate_uses_refs(
    refs: set[str], user_files: set[Path]
) -> dict[str, list[Path]]:
    """Search user files for each ref string and return a mapping of ref to files.

    Reads each file once and checks whether each ref string appears in the
    file content.

    Args:
        refs: Set of ``uses:`` reference strings to search for
            (e.g. ``"actions/checkout@v4"``).
        user_files: Set of absolute file paths to search in.

    Returns:
        Mapping of ref string to the list of files containing it. Refs not
        found in any user file are omitted.
    """
    # Read all files once
    file_contents: dict[Path, str] = {}
    for path in user_files:
        try:
            file_contents[path] = path.read_text()
        except OSError:
            continue

    result: dict[str, list[Path]] = {}
    for ref in refs:
        matching: list[Path] = []
        for path, content in file_contents.items():
            if ref in content:
                matching.append(path)
        if matching:
            # Sort for deterministic output
            result[ref] = sorted(matching)

    return result
