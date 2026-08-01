"""ghagen CLI — generate GitHub Actions workflows from Python."""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

import typer
import typer.core
import typer.main

# `uv.lock` pins typer 0.24.1, which depends on the top-level `click` 8.3.2
# distribution rather than vendoring it. These are the exception types click
# raises out of `command.main()` under `standalone_mode=False`.
from click.exceptions import Abort, ClickException
from typer import rich_utils

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
            timeout_minutes=10,
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


def main(argv: Sequence[str] | None = None) -> int:
    """Run the CLI. Returns the exit code.

    The entry point is this function, not the Typer app: click runs in
    ``standalone_mode=False`` so the exit code comes back as a value instead of
    being handed to ``sys.exit`` from inside the framework. The codes are the
    shared contract in ``fixtures/cli-exit-codes.yml`` -- ``0`` success, ``1``
    expected failure, ``2`` usage error -- which both ports drive through their
    ``main()``.

    Turning standalone mode off also turns off the framework's error
    *rendering*, so the handlers below reproduce Typer's own (``typer/core.py``
    ``_main``, the ``ClickException`` and ``Abort`` branches). Calling
    ``exc.show()`` instead would silently downgrade every error to click's
    plain renderer; ``tests/test_cli/test_exit_codes.py`` guards that.

    ``app`` stays exported for ``typer.testing.CliRunner``.
    """
    command = typer.main.get_command(app)
    # `get_command` is typed as returning a plain click `Command`; the markup
    # mode is a Typer attribute. Reading it defensively keeps the fallback
    # identical to Typer's own non-rich branch.
    markup_mode = getattr(command, "rich_markup_mode", None)
    rich = typer.core.HAS_RICH and markup_mode is not None
    try:
        return (
            command.main(
                args=None if argv is None else list(argv),
                prog_name="ghagen",
                standalone_mode=False,
            )
            or 0
        )
    except ClickException as exc:
        if rich:
            rich_utils.rich_format_error(exc)
        else:
            exc.show()
        return exc.exit_code
    except Abort:
        if rich:
            rich_utils.rich_abort_error()
        else:
            typer.echo("Aborted!", err=True)
        return 1
