"""Shared CLI helpers used by both the top-level app and sub-apps."""

from __future__ import annotations

import importlib.util
import sys
import tomllib
from pathlib import Path

import typer

from ghagen.app import App

CONFIG_SEARCH_PATHS = [
    ".github/ghagen_workflows.py",
    "ghagen_config.py",
]

GHAGEN_TOML_PATH = Path(".github/ghagen.toml")


def _entrypoint_from_ghagen_toml(cwd: Path) -> Path | None:
    """Return the configured entrypoint path, or ``None`` if not set.

    Reads ``.github/ghagen.toml`` (relative to *cwd*), extracts the
    top-level ``entrypoint`` key, and resolves it relative to the toml
    file's directory. Returns ``None`` if the file or key is absent.
    Raises ``typer.Exit(1)`` on malformed TOML, a wrong-type value, or
    a resolved path that does not exist.
    """
    ghagen_toml = cwd / GHAGEN_TOML_PATH
    if not ghagen_toml.is_file():
        return None

    try:
        with ghagen_toml.open("rb") as f:
            data = tomllib.load(f)
    except tomllib.TOMLDecodeError as exc:
        typer.echo(f"Error: {ghagen_toml}: failed to parse TOML: {exc}", err=True)
        raise typer.Exit(1) from exc

    raw = data.get("entrypoint")
    if raw is None:
        return None
    if not isinstance(raw, str):
        typer.echo(
            f"Error: {ghagen_toml}: 'entrypoint' must be a string, "
            f"got {type(raw).__name__}",
            err=True,
        )
        raise typer.Exit(1)

    resolved = (ghagen_toml.parent / raw).resolve()
    if not resolved.is_file():
        typer.echo(
            f"Error: {ghagen_toml}: entrypoint '{raw}' does not exist "
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

    from_toml = _entrypoint_from_ghagen_toml(Path.cwd())
    if from_toml is not None:
        return from_toml

    for candidate in CONFIG_SEARCH_PATHS:
        path = Path(candidate)
        if path.exists():
            return path

    typer.echo(
        "Error: no config file found. Searched:\n"
        + "\n".join(f"  - {p}" for p in CONFIG_SEARCH_PATHS)
        + f"\n  - {GHAGEN_TOML_PATH} (top-level 'entrypoint' key)\n"
        "\nUse --config to specify a path, set 'entrypoint' in "
        f"{GHAGEN_TOML_PATH}, or run `ghagen init` to create one.",
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
