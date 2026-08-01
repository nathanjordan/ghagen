"""Shared CLI helpers used by both the top-level app and sub-apps.

Discovery + parse + validation live in :mod:`ghagen.config` and return typed
values. This module is the *render* layer: it maps :class:`ConfigError` values
to ``typer.Exit``, exactly as :mod:`ghagen.pin.engine` renders its typed report.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import typer

from ghagen.app import App
from ghagen.config import (
    CONFIG_SEARCH_PATHS,
    GHAGEN_YML_MARKER,
    load_project_config,
    resolve_app,
)


def _find_config(config: str | None) -> Path:
    """Locate the workflow config file, rendering config errors and exiting."""
    project = load_project_config(cli_config_flag=config)
    if project.errors:
        for err in project.errors:
            typer.echo(f"Error: {err.message}", err=True)
        raise typer.Exit(1)

    if project.config_path is not None:
        return project.config_path

    typer.echo(
        "Error: no config file found. Searched:\n"
        + "\n".join(f"  - {p}" for p in CONFIG_SEARCH_PATHS)
        + f"\n  - {GHAGEN_YML_MARKER} (top-level 'entrypoint' key)\n"
        "\nUse --config to specify a path, set 'entrypoint' in "
        f"{GHAGEN_YML_MARKER}, or run `ghagen init` to create one.",
        err=True,
    )
    raise typer.Exit(1)


def _load_app(config_path: Path) -> App:
    """Dynamically import the config file and extract the App instance.

    The config's parent directory is on ``sys.path`` for the duration of the
    import *and* of App resolution — a helper imported lazily inside
    ``create_app()`` must still resolve (ADR-0004) — and is removed again
    afterwards, so loading a config does not permanently widen the host
    process's module search path. The module -> App *policy* lives in
    :func:`ghagen.config.resolve_app`, whose error value is rendered below.
    """
    spec = importlib.util.spec_from_file_location("ghagen_config", config_path)
    if spec is None or spec.loader is None:
        typer.echo(f"Error: cannot load {config_path}", err=True)
        raise typer.Exit(1)

    # Add parent dir to sys.path so relative imports work, scoped to the window
    # below. The window must span BOTH statements: ``resolve_app`` invokes
    # ``create_app()``, and a helper imported lazily in there resolves through
    # this entry (ADR-0004).
    parent = str(config_path.parent.resolve())
    inserted = parent not in sys.path
    if inserted:
        sys.path.insert(0, parent)

    module = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(module)
        app, error = resolve_app(module, config_path)
    finally:
        # Remove by index after checking identity, and only if this call did
        # the inserting.
        if inserted and sys.path and sys.path[0] == parent:
            del sys.path[0]

    # The typer.Exit path sits outside the try, so the entry is already gone by
    # the time the CLI renders the error.
    if error is not None:
        typer.echo(f"Error: {error.message}", err=True)
        raise typer.Exit(1)
    assert app is not None
    return app
