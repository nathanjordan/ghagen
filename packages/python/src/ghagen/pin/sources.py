"""Determine which Python source files contain each ``uses:`` ref string.

Distinguishes between user-authored files and ghagen internal files so that
the update command can propose edits only in user-controlled sources.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from ghagen._package_paths import is_user_file
from ghagen.config import resolve_app

if TYPE_CHECKING:
    from ghagen.app import App


def track_user_files(config_path: Path) -> tuple[App, set[Path]]:
    """Load the app and discover the user files loaded as a side effect.

    Imports *config_path* directly and resolves its :class:`~ghagen.app.App`
    through the shared :func:`ghagen.config.resolve_app` policy — no injected
    loader. Snapshots ``sys.modules`` around the import, then filters the newly
    imported modules to only user-authored files (excluding stdlib,
    site-packages, and the ghagen package itself) via
    :func:`ghagen._package_paths.is_user_file`. Returns both the loaded
    :class:`~ghagen.app.App` and the tracked files so callers need no
    mutable-closure hack to smuggle the app out.

    :func:`importlib.util.exec_module` does not register the config module in
    ``sys.modules``; *config_path* is therefore added explicitly.

    Args:
        config_path: Path to the user's ghagen config file.

    Returns:
        ``(app, files)`` where *files* is a set of absolute
        :class:`~pathlib.Path` objects for user source files.

    Raises:
        RuntimeError: If *config_path* cannot be loaded or does not expose a
            usable :class:`~ghagen.app.App`.
    """
    spec = importlib.util.spec_from_file_location("ghagen_config", config_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"cannot load {config_path}")

    # Add parent dir to sys.path so the config's relative imports resolve.
    parent = str(config_path.parent.resolve())
    if parent not in sys.path:
        sys.path.insert(0, parent)

    module = importlib.util.module_from_spec(spec)

    # Resolve the App INSIDE the snapshot window: a module imported lazily
    # inside ``create_app()`` (rather than at config import time) is only added
    # to ``sys.modules`` when ``resolve_app`` invokes the factory. Snapshotting
    # ``after`` before that call would miss such helpers, silently leaving their
    # ``uses:`` refs un-rewritten (ADR-0004's defended failure mode).
    before = set(sys.modules.keys())
    spec.loader.exec_module(module)
    app, error = resolve_app(module, config_path)
    after = set(sys.modules.keys())

    if error is not None:
        raise RuntimeError(error.message)
    assert app is not None

    new_modules = after - before

    user_files: set[Path] = set()
    for mod_name in new_modules:
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        mod_file = getattr(mod, "__file__", None)
        if mod_file is None:
            continue
        path = Path(mod_file).resolve()
        if is_user_file(path):
            user_files.add(path)

    # exec_module does not register the config module in sys.modules, so the
    # snapshot above never sees it — add it explicitly.
    resolved_config = config_path.resolve()
    if is_user_file(resolved_config):
        user_files.add(resolved_config)

    return app, user_files


def locate_uses_refs(refs: set[str], user_files: set[Path]) -> dict[str, list[Path]]:
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
