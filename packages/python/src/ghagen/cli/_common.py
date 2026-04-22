"""Shared CLI helpers used by both the top-level app and sub-apps."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import typer

from ghagen._yaml_config import load_yaml_config
from ghagen.app import App

CONFIG_SEARCH_PATHS = [
    ".github/ghagen_workflows.py",
    "ghagen_config.py",
]

GHAGEN_YML_PATH = Path(".ghagen.yml")


def _entrypoint_from_ghagen_yml(cwd: Path) -> Path | None:
    """Return the configured entrypoint path, or ``None`` if not set.

    Reads ``.ghagen.yml`` (relative to *cwd*), extracts the top-level
    ``entrypoint`` key, and resolves it relative to the yml file's
    parent directory (the repo root). Returns ``None`` if the file or
    key is absent. Raises ``typer.Exit(1)`` on malformed YAML, a
    wrong-type value, or a resolved path that does not exist.
    """
    ghagen_yml = cwd / GHAGEN_YML_PATH
    if not ghagen_yml.is_file():
        return None

    try:
        data = load_yaml_config(ghagen_yml)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(1) from exc

    raw = data.get("entrypoint")
    if raw is None:
        return None
    if not isinstance(raw, str):
        typer.echo(
            f"Error: {ghagen_yml}: 'entrypoint' must be a string, "
            f"got {type(raw).__name__}",
            err=True,
        )
        raise typer.Exit(1)

    resolved = (ghagen_yml.parent / raw).resolve()
    if not resolved.is_file():
        typer.echo(
            f"Error: {ghagen_yml}: entrypoint '{raw}' does not exist "
            f"(resolved to {resolved})",
            err=True,
        )
        raise typer.Exit(1)
    return resolved


def _find_config(config: str | None) -> Path:
    """Locate the workflow config file."""
    if config:
        path = Path(config)
        if not path.exists():
            typer.echo(f"Error: config file not found: {path}", err=True)
            raise typer.Exit(1)
        return path

    from_yml = _entrypoint_from_ghagen_yml(Path.cwd())
    if from_yml is not None:
        return from_yml

    for candidate in CONFIG_SEARCH_PATHS:
        path = Path(candidate)
        if path.exists():
            return path

    typer.echo(
        "Error: no config file found. Searched:\n"
        + "\n".join(f"  - {p}" for p in CONFIG_SEARCH_PATHS)
        + f"\n  - {GHAGEN_YML_PATH} (top-level 'entrypoint' key)\n"
        "\nUse --config to specify a path, set 'entrypoint' in "
        f"{GHAGEN_YML_PATH}, or run `ghagen init` to create one.",
        err=True,
    )
    raise typer.Exit(1)


def _load_app(config_path: Path) -> App:
    """Dynamically import the config file and extract the App instance."""
    spec = importlib.util.spec_from_file_location("ghagen_config", config_path)
    if spec is None or spec.loader is None:
        typer.echo(f"Error: cannot load {config_path}", err=True)
        raise typer.Exit(1)

    # Add parent dir to sys.path so relative imports work
    parent = str(config_path.parent.resolve())
    if parent not in sys.path:
        sys.path.insert(0, parent)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # Look for app variable or create_app function
    if hasattr(module, "create_app"):
        result = module.create_app()
        if not isinstance(result, App):
            typer.echo(
                f"Error: create_app() in {config_path} must return an App instance",
                err=True,
            )
            raise typer.Exit(1)
        return result

    if hasattr(module, "app"):
        result = module.app
        if not isinstance(result, App):
            typer.echo(
                f"Error: 'app' in {config_path} must be an App instance",
                err=True,
            )
            raise typer.Exit(1)
        return result

    typer.echo(
        f"Error: {config_path} must define 'app = App(...)'"
        " or 'def create_app() -> App'",
        err=True,
    )
    raise typer.Exit(1)
