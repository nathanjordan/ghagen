"""ghagen deps — manage action dependencies.

Each command is a thin shell: resolve the config/app, build a
:class:`~ghagen.pin.github.GitHubClient`, call the pin engine, and render the
typed report.  All orchestration lives in :mod:`ghagen.pin.engine`.
"""

from __future__ import annotations

import json as json_mod
import os
from pathlib import Path
from typing import TYPE_CHECKING

import typer

from ghagen.cli._common import _find_config, _load_app

if TYPE_CHECKING:
    from ghagen.app import App
    from ghagen.pin.engine import LockfileStaleEntry, VersionBump
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
    json: bool = typer.Option(
        False, "--json", help="Output in machine-readable JSON format"
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
    from ghagen.pin.sources import track_user_files

    if mode not in ("versions", "lockfile", "all"):
        typer.echo(
            f"Error: unknown --mode value '{mode}' (valid: versions, lockfile, all)",
            err=True,
        )
        raise typer.Exit(2)

    apply = not check

    config_path = _find_config(config)

    # Load the app while tracking the user source files it imported.
    ghagen_app, user_files = track_user_files(config_path, _load_app)

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
        typer.echo("Applied version bumps:")
        for f in report.changed_files:
            typer.echo(f"  modified {f}")

    check_versions = mode in ("versions", "all")
    check_lockfile = mode in ("lockfile", "all")

    if not report.version_bumps and not report.lockfile_stale:
        if json:
            typer.echo(
                json_mod.dumps(
                    {"version_bumps": [], "lockfile_stale": []},
                    indent=2,
                )
            )
        else:
            typer.echo("Everything is up to date.")
        raise typer.Exit(0)

    if json:
        result: dict = {}
        if check_versions:
            result["version_bumps"] = [
                _bump_to_json(bump) for bump in report.version_bumps
            ]
        if check_lockfile:
            result["lockfile_stale"] = [
                _stale_to_json(entry) for entry in report.lockfile_stale
            ]
        typer.echo(json_mod.dumps(result, indent=2))
    else:
        _print_human_report(report.version_bumps, report.lockfile_stale)


def _bump_to_json(bump: VersionBump) -> dict:
    """Serialize a version bump for ``--json`` (omitting empty ``source_files``)."""
    entry: dict = {
        "uses": bump.uses,
        "current": bump.current,
        "latest": bump.latest,
        "severity": bump.severity,
    }
    if bump.source_files:
        entry["source_files"] = list(bump.source_files)
    return entry


def _stale_to_json(stale: LockfileStaleEntry) -> dict:
    """Serialize a stale entry for ``--json`` (omitting empty ``source_files``)."""
    entry: dict = {
        "uses": stale.uses,
        "current_sha": stale.current_sha,
        "latest_sha": stale.latest_sha,
    }
    if stale.source_files:
        entry["source_files"] = list(stale.source_files)
    return entry


def _print_human_report(
    version_bumps: list[VersionBump],
    lockfile_stale: list[LockfileStaleEntry],
) -> None:
    """Print a human-readable upgrade report."""
    if version_bumps:
        typer.echo("Version updates available:")
        typer.echo("")
        for bump in version_bumps:
            typer.echo(f"  {bump.uses}  →  {bump.latest}  [{bump.severity}]")
            for src in bump.source_files:
                typer.echo(f"    in {src}")
        typer.echo("")

    if lockfile_stale:
        typer.echo("Stale lockfile entries:")
        typer.echo("")
        for entry in lockfile_stale:
            typer.echo(f"  {entry.uses}")
            typer.echo(f"    current SHA: {entry.current_sha[:12]}...")
            typer.echo(f"    latest SHA:  {entry.latest_sha[:12]}...")
        typer.echo("")
