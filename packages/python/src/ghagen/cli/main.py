"""ghagen CLI — generate GitHub Actions workflows from Python."""

from __future__ import annotations

from pathlib import Path

import typer

from ghagen.cli._common import _find_config, _load_app
from ghagen.cli.deps import deps_app

app = typer.Typer(
    name="ghagen",
    help="Generate GitHub Actions workflow YAML from Python code.",
    no_args_is_help=True,
)

app.add_typer(deps_app, name="deps")


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

    typer.echo(f"Synthesized {len(written)} file(s).")


@app.command("check-synced")
def check_synced(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
) -> None:
    """Check if generated YAML files are up-to-date."""
    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)

    stale = ghagen_app.check()
    if not stale:
        typer.echo("All files are up-to-date.")
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

from ghagen import App, Job, On, PRTrigger, PushTrigger, Step, Workflow

app = App()

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

app.add_workflow(ci, "ci.yml")
'''
    )

    typer.echo(f"Created {config_path}")
    typer.echo("Run `ghagen synth` to generate workflow YAML files.")
