"""ghagen deps — manage action dependencies.

Each command is a thin shell: resolve the config/app, build a
:class:`~ghagen.pin.github.GitHubClient`, call the pin engine, and render the
typed report.  All orchestration lives in :mod:`ghagen.pin.engine`.
"""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from ghagen.cli._common import _find_config, _load_app

if TYPE_CHECKING:
    from ghagen.app import App
    from ghagen.pin.github import GitHubClient

deps_app = typer.Typer(
    help="Manage action dependencies.",
    no_args_is_help=True,
)


def _ensure_lockfile_path(app: App) -> Path:
    """Return the app's absolute lockfile path, or exit 1 if disabled."""
    if app.lockfile_path is None:
        typer.echo("Error: lockfile is disabled (lockfile=None on App)", err=True)
        raise typer.Exit(1)
    return app.root / app.lockfile_path


def _github_client(token: str | None) -> GitHubClient:
    """Resolve the token (flag > $GITHUB_TOKEN > $GH_TOKEN) and build a client.

    Emits the no-token warning once, here, so the individual commands stay free
    of duplicated lookup + warning logic.
    """
    from ghagen.pin.github import GitHubClient

    gh_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not gh_token:
        typer.echo(
            "warning: no GitHub token found. Using unauthenticated requests "
            "(60 req/hr limit). Set $GITHUB_TOKEN or use --token.",
            err=True,
        )
    return GitHubClient(token=gh_token)


@deps_app.command("pin")
def deps_pin(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    update: bool = typer.Option(
        False, "--update", help="Re-resolve all entries to latest SHAs"
    ),
    prune: bool = typer.Option(
        True,
        "--prune/--no-prune",
        help="Remove lockfile entries not referenced in code",
    ),
    token: str | None = typer.Option(
        None, "--token", help="GitHub token (default: $GITHUB_TOKEN)"
    ),
) -> None:
    """Pin action references to commit SHAs in a lockfile."""
    from ghagen.pin.engine import pin as pin_engine

    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)
    _ensure_lockfile_path(ghagen_app)  # validate before doing any work

    client = _github_client(token)

    report = pin_engine(ghagen_app, client, update=update, prune=prune)

    for resolved in report.resolved:
        typer.echo(f"  {resolved.uses} → {resolved.sha[:12]}")
    for warning in report.warnings:
        typer.echo(f"warning: {warning}", err=True)
    for error in report.errors:
        typer.echo(f"error: {error}", err=True)
    if report.pruned:
        typer.echo(f"Pruned {report.pruned} stale entry/entries.")
    if report.written:
        typer.echo(f"Wrote {report.lockfile_path}")
    if report.up_to_date:
        typer.echo("Lockfile is already up to date.")

    if report.errors:
        typer.echo(f"{len(report.errors)} ref(s) failed to resolve.", err=True)
        raise typer.Exit(1)


@deps_app.command("check-synced")
def deps_check_synced(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    prune: bool = typer.Option(
        True,
        "--prune/--no-prune",
        help="Also flag stale lockfile entries not referenced in code",
    ),
) -> None:
    """Verify lockfile is in sync with code (exit 1 if stale)."""
    from ghagen.pin.engine import check_sync

    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)
    _ensure_lockfile_path(ghagen_app)  # validate before doing any work

    report = check_sync(ghagen_app, prune=prune)

    if report.in_sync:
        typer.echo("Lockfile is in sync.")
        raise typer.Exit(0)

    if report.missing:
        typer.echo("Missing lockfile entries:", err=True)
        for ref in report.missing:
            typer.echo(f"  {ref}", err=True)
    if report.extra:
        typer.echo("Stale lockfile entries:", err=True)
        for ref in report.extra:
            typer.echo(f"  {ref}", err=True)
    raise typer.Exit(1)


@deps_app.command("upgrade")
def deps_upgrade(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    check: bool = typer.Option(
        False, "--check", help="Check for available upgrades without applying"
    ),
    output_format: str | None = typer.Option(
        None,
        "--format",
        help=(
            "Output format: 'json', 'pr-body', or 'issue-body' "
            "(default: human-readable text)"
        ),
    ),
    mode: str = typer.Option(
        "all",
        "--mode",
        help="Detection mode: 'versions', 'lockfile', or 'all' (default)",
    ),
    token: str | None = typer.Option(
        None, "--token", help="GitHub token (default: $GITHUB_TOKEN)"
    ),
) -> None:
    """Upgrade action dependencies to latest versions."""
    from ghagen.pin.engine import upgrade as upgrade_engine
    from ghagen.pin.render import render_upgrade_report
    from ghagen.pin.sources import track_user_files

    if mode not in ("versions", "lockfile", "all"):
        typer.echo(
            f"Error: unknown --mode value '{mode}' (valid: versions, lockfile, all)",
            err=True,
        )
        raise typer.Exit(2)

    valid_formats = ("json", "pr-body", "issue-body")
    if output_format is not None and output_format not in valid_formats:
        typer.echo(
            f"Error: unknown --format value '{output_format}' "
            "(valid: json, pr-body, issue-body)",
            err=True,
        )
        raise typer.Exit(2)

    apply = not check

    config_path = _find_config(config)

    # Load the app while tracking the user source files it imported.
    ghagen_app, user_files = track_user_files(config_path)

    client = _github_client(token)

    report = upgrade_engine(
        ghagen_app,
        client,
        user_files,
        mode=mode,  # type: ignore[arg-type]
        apply=apply,
    )

    for warning in report.warnings:
        typer.echo(f"warning: {warning}", err=True)

    if report.changed_files:
        # Under --format the report itself owns stdout; this progress note goes
        # to stderr so `--format json` (without --check) stays machine-parseable.
        progress_to_stderr = output_format is not None
        typer.echo("Applied version bumps:", err=progress_to_stderr)
        for f in report.changed_files:
            typer.echo(f"  modified {f}", err=progress_to_stderr)

    typer.echo(
        render_upgrade_report(report, output_format=output_format or "text"),
        nl=False,
    )


def _reject_newlines(**values: str) -> None:
    """Exit 2 if any value spans lines.

    These reach ``$GITHUB_OUTPUT`` as ``key=value`` lines, so an embedded
    newline forges additional outputs -- an injection vector, since every one
    of them is a workflow-author-supplied action input.  Rejecting at the edge
    is what lets :func:`~ghagen.pin.plan.render_update_plan` stay single-line
    per field and skip the heredoc-delimiter machinery entirely.
    """
    for name, value in values.items():
        if "\n" in value or "\r" in value:
            typer.echo(f"Error: --{name} must not contain a newline", err=True)
            raise typer.Exit(2)


@deps_app.command("update")
def deps_update(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    mode: str = typer.Option(
        "all",
        "--mode",
        help="Detection mode: 'versions', 'lockfile', or 'all' (default)",
    ),
    output: str = typer.Option(
        "pr", "--output", help="What to raise when there is something: 'pr' or 'issue'"
    ),
    output_format: str = typer.Option(
        "github",
        "--format",
        help="Plan format: 'github' ($GITHUB_OUTPUT key=value, default) or 'json'",
    ),
    branch_prefix: str = typer.Option(
        "ghagen-update/", "--branch-prefix", help="Prefix for the dated PR branch"
    ),
    commit_message_prefix: str = typer.Option(
        "", "--commit-message-prefix", help="Prefix for the commit subject"
    ),
    labels: str = typer.Option(
        "", "--labels", help="Comma-separated labels for the PR or issue"
    ),
    body_file: str | None = typer.Option(
        None, "--body-file", help="Write the PR/issue body to this path"
    ),
    dry_run: bool = typer.Option(
        False, "--dry-run", help="Decide everything, write nothing"
    ),
    token: str | None = typer.Option(
        None, "--token", help="GitHub token (default: $GITHUB_TOKEN)"
    ),
) -> None:
    """Sweep for dependency updates, apply them, and print the resulting plan.

    One command per automation run.  It performs every write the update needs
    -- version bumps in user source, and the lockfile re-resolve when, and only
    when, that is the right thing to do -- and prints what the caller should
    raise.  A caller reads the plan and acts on it; it never reconstructs a
    decision from ``deps upgrade --format json``, which cannot answer the
    lockfile question because the payload does not carry ``app.lockfile_path``.

    Stdout carries the plan and nothing else, so ``--format github`` can be a
    bare ``>> "$GITHUB_OUTPUT"`` redirect.  Warnings and progress go to stderr.
    """
    from ghagen.pin.engine import pin as pin_engine
    from ghagen.pin.engine import upgrade as upgrade_engine
    from ghagen.pin.plan import plan_update, render_update_plan
    from ghagen.pin.render import render_upgrade_report
    from ghagen.pin.sources import track_user_files

    if mode not in ("versions", "lockfile", "all"):
        typer.echo(
            f"Error: unknown --mode value '{mode}' (valid: versions, lockfile, all)",
            err=True,
        )
        raise typer.Exit(2)
    if output not in ("pr", "issue"):
        typer.echo(
            f"Error: unknown --output value '{output}' (valid: pr, issue)", err=True
        )
        raise typer.Exit(2)
    if output_format not in ("github", "json"):
        typer.echo(
            f"Error: unknown --format value '{output_format}' (valid: github, json)",
            err=True,
        )
        raise typer.Exit(2)
    _reject_newlines(
        **{
            "branch-prefix": branch_prefix,
            "commit-message-prefix": commit_message_prefix,
            "labels": labels,
        }
    )

    config_path = _find_config(config)
    ghagen_app, user_files = track_user_files(config_path)
    client = _github_client(token)

    report = upgrade_engine(
        ghagen_app,
        client,
        user_files,
        mode=mode,  # type: ignore[arg-type]
        apply=not dry_run,
    )
    for warning in report.warnings:
        typer.echo(f"warning: {warning}", err=True)

    plan = plan_update(
        ghagen_app,
        report,
        output=output,  # type: ignore[arg-type]
        branch_prefix=branch_prefix,
        commit_message_prefix=commit_message_prefix,
        labels=labels,
        # Read here, at the edge, and injected: `plan_update` has no clock, for
        # the reason ADR-0002 gives about construction-time globals.
        today=datetime.now(tz=UTC).date(),
    )

    changed = bool(report.changed_files)
    for f in report.changed_files:
        typer.echo(f"  modified {f}", err=True)

    if plan.refresh_lockfile and not dry_run:
        # Reached only when the app *has* a lockfile -- the plan decided that,
        # holding the App, which is why no `_ensure_lockfile_path` guard (and
        # no exit 1) is possible here.
        pin_report = pin_engine(ghagen_app, client, update=True, prune=True)
        for warning in pin_report.warnings:
            typer.echo(f"warning: {warning}", err=True)
        for error in pin_report.errors:
            typer.echo(f"error: {error}", err=True)
        if pin_report.errors:
            # Do not print a plan telling the caller to raise a PR for a tree
            # whose lockfile refresh failed.
            typer.echo(f"{len(pin_report.errors)} ref(s) failed to resolve.", err=True)
            raise typer.Exit(1)
        if pin_report.written:
            typer.echo(f"  modified {pin_report.lockfile_path}", err=True)
            changed = True

    if body_file is not None and plan.body_format is not None:
        Path(body_file).write_text(
            render_upgrade_report(report, output_format=plan.body_format)
        )

    typer.echo(
        render_update_plan(plan, changed=changed, output_format=output_format),  # type: ignore[arg-type]
        nl=False,
    )
