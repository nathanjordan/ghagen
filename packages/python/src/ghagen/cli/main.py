"""ghagen CLI — generate GitHub Actions workflows from Python."""

from __future__ import annotations

from pathlib import Path

import typer

from ghagen.cli._common import _find_config, _load_app
from ghagen.cli.deps import deps_app
from ghagen.lint import (
    format_github,
    format_human,
    format_json,
    load_config,
    run_lint,
)
from ghagen.lint.rules import ALL_RULES
from ghagen.lint.violation import Severity

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
def lint(
    config: str | None = typer.Option(
        None,
        "--config",
        "-c",
        help="Path to ghagen_workflows.py config file",
    ),
    format: str = typer.Option(  # noqa: A002 — matches ruff/pyright UX
        "human",
        "--format",
        "-f",
        help="Output format: human, json, or github",
    ),
    disable: list[str] = typer.Option(  # noqa: B008
        [],
        "--disable",
        help="Disable a rule by ID (repeatable)",
    ),
    list_rules: bool = typer.Option(
        False,
        "--list-rules",
        help="List available rules and exit",
    ),
) -> None:
    """Lint ghagen workflow definitions for common problems."""
    if list_rules:
        for rule_fn in ALL_RULES:
            meta = rule_fn.meta
            typer.echo(
                f"{meta.id} ({meta.default_severity.value})\n  {meta.description}"
            )
        raise typer.Exit(0)

    # Load lint config — separate from the ghagen_workflows.py config
    try:
        lint_config, warnings = load_config(Path.cwd(), cli_disable=disable)
    except ValueError as exc:
        typer.echo(f"Error: {exc}", err=True)
        raise typer.Exit(2) from exc

    for warning in warnings:
        typer.echo(f"warning: {warning}", err=True)

    # Load the user's App from ghagen_workflows.py
    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)

    # Run the lint rules
    violations = run_lint(ghagen_app, lint_config)

    # Render in the requested format
    if format == "human":
        typer.echo(format_human(violations), nl=False)
    elif format == "json":
        typer.echo(format_json(violations))
    elif format == "github":
        typer.echo(format_github(violations), nl=False)
    else:
        typer.echo(
            f"Error: unknown --format value '{format}' (valid: human, json, github)",
            err=True,
        )
        raise typer.Exit(2)

    # Exit 1 only if there are error-severity violations
    if any(v.severity == Severity.ERROR for v in violations):
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
