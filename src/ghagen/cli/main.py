"""ghagen CLI — generate GitHub Actions workflows from Python."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import typer

from ghagen.app import App

app = typer.Typer(
    name="ghagen",
    help="Generate GitHub Actions workflow YAML from Python code.",
    no_args_is_help=True,
)

CONFIG_SEARCH_PATHS = [
    ".github/ghagen_workflows.py",
    "ghagen_config.py",
]


def _find_config(config: str | None) -> Path:
    """Locate the workflow config file."""
    if config:
        path = Path(config)
        if not path.exists():
            typer.echo(f"Error: config file not found: {path}", err=True)
            raise typer.Exit(1)
        return path

    for candidate in CONFIG_SEARCH_PATHS:
        path = Path(candidate)
        if path.exists():
            return path

    typer.echo(
        "Error: no config file found. Searched:\n"
        + "\n".join(f"  - {p}" for p in CONFIG_SEARCH_PATHS)
        + "\n\nUse --config to specify a path, or run `ghagen init` to create one.",
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


@app.command()
def synth(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Generate workflow YAML files from Python definitions."""
    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)

    written = ghagen_app.synth()
    for path in written:
        typer.echo(f"  wrote {path}")

    typer.echo(f"Synthesized {len(written)} workflow(s).")


@app.command()
def check(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Check if generated YAML files are up-to-date."""
    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)

    stale = ghagen_app.check()
    if not stale:
        typer.echo("All workflow files are up-to-date.")
        raise typer.Exit(0)

    typer.echo(f"{len(stale)} file(s) are out of date:\n", err=True)
    for path, diff in stale:
        typer.echo(f"--- {path} ---", err=True)
        typer.echo(diff, err=True)

    raise typer.Exit(1)


@app.command()
def init(
    outdir: str = typer.Option(".github", "--outdir", "-o", help="Output directory"),
) -> None:
    """Scaffold a minimal ghagen config file."""
    config_path = Path(outdir) / "ghagen_workflows.py"

    if config_path.exists():
        typer.echo(f"Config file already exists: {config_path}", err=True)
        raise typer.Exit(1)

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(
        '''\
"""GitHub Actions workflow definitions."""

from ghagen import Workflow, Job, Step, On
from ghagen.app import App
from ghagen.models.trigger import PushTrigger, PRTrigger

app = App(outdir=".github/workflows")

ci = Workflow(
    name="CI",
    on=On(
        push=PushTrigger(branches=["main"]),
        pull_request=PRTrigger(branches=["main"]),
    ),
    jobs={
        "test": Job(
            runs_on="ubuntu-latest",
            steps=[
                Step(uses="actions/checkout@v4"),
                Step(name="Run tests", run="echo 'Add your test command here'"),
            ],
        ),
    },
)

app.add(ci, filename="ci.yml")
'''
    )

    typer.echo(f"Created {config_path}")
    typer.echo("Run `ghagen synth` to generate workflow YAML files.")
