"""ghagen deps — manage action dependencies."""

from __future__ import annotations

import json as json_mod
import os
from datetime import UTC, datetime
from pathlib import Path

import typer

from ghagen.app import App
from ghagen.cli._common import _find_config, _load_app

deps_app = typer.Typer(
    help="Manage action dependencies.",
    no_args_is_help=True,
)


@deps_app.command("pin")
def deps_pin(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    update: bool = typer.Option(
        False, "--update", help="Re-resolve all entries to latest SHAs"
    ),
    prune: bool = typer.Option(
        True, "--prune/--no-prune", help="Remove lockfile entries not referenced in code"
    ),
    token: str | None = typer.Option(
        None, "--token", help="GitHub token (default: $GITHUB_TOKEN)"
    ),
) -> None:
    """Pin action references to commit SHAs in a lockfile."""
    from ghagen.pin.collect import collect_uses_refs
    from ghagen.pin.lockfile import (
        PinEntry,
        read_lockfile,
        write_lockfile,
    )
    from ghagen.pin.resolve import ResolveError, parse_uses, resolve_ref

    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)

    # Resolve lockfile path from the app.
    if ghagen_app.lockfile_path is None:
        typer.echo("Error: lockfile is disabled (lockfile=None on App)", err=True)
        raise typer.Exit(1)

    lockfile_full = ghagen_app.root / ghagen_app.lockfile_path

    # Collect all uses: refs from the app.
    refs = collect_uses_refs(ghagen_app)

    # Read existing lockfile.
    lockfile = read_lockfile(lockfile_full)

    # Resolve token: flag > $GITHUB_TOKEN > $GH_TOKEN.
    gh_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not gh_token:
        typer.echo(
            "warning: no GitHub token found. Using unauthenticated requests "
            "(60 req/hr limit). Set $GITHUB_TOKEN or use --token.",
            err=True,
        )

    # Determine which refs need resolution.
    to_resolve = refs if update else refs - set(lockfile.pins)

    # Resolve refs via GitHub API.
    now = datetime.now(UTC)
    resolved = 0
    errors = 0

    for uses in sorted(to_resolve):
        try:
            parsed = parse_uses(uses)
        except ValueError as exc:
            typer.echo(f"warning: skipping {uses!r}: {exc}", err=True)
            continue

        try:
            sha = resolve_ref(
                parsed.owner, parsed.repo, parsed.ref, token=gh_token
            )
        except ResolveError as exc:
            typer.echo(f"error: {uses}: {exc}", err=True)
            errors += 1
            continue

        lockfile.pins[uses] = PinEntry(sha=sha, resolved_at=now)
        resolved += 1
        typer.echo(f"  {uses} → {sha[:12]}")

    # Prune stale entries.
    pruned = 0
    if prune:
        pruned = lockfile.prune(refs)
        if pruned:
            typer.echo(f"Pruned {pruned} stale entry/entries.")

    # Write lockfile if anything changed.
    if resolved or pruned:
        write_lockfile(lockfile, lockfile_full)
        typer.echo(f"Wrote {lockfile_full}")

    if not to_resolve and not pruned:
        typer.echo("Lockfile is already up to date.")

    if errors:
        typer.echo(f"{errors} ref(s) failed to resolve.", err=True)
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
    from ghagen.pin.collect import collect_uses_refs
    from ghagen.pin.lockfile import read_lockfile

    config_path = _find_config(config)
    ghagen_app = _load_app(config_path)

    # Resolve lockfile path from the app.
    if ghagen_app.lockfile_path is None:
        typer.echo("Error: lockfile is disabled (lockfile=None on App)", err=True)
        raise typer.Exit(1)

    lockfile_full = ghagen_app.root / ghagen_app.lockfile_path

    # Collect all uses: refs from the app.
    refs = collect_uses_refs(ghagen_app)

    # Read existing lockfile.
    lockfile = read_lockfile(lockfile_full)

    # Verify lockfile covers all refs and nothing is stale.
    missing = refs - set(lockfile.pins)
    extra = set(lockfile.pins) - refs if prune else set()
    if missing or extra:
        if missing:
            typer.echo("Missing lockfile entries:", err=True)
            for ref in sorted(missing):
                typer.echo(f"  {ref}", err=True)
        if extra:
            typer.echo("Stale lockfile entries:", err=True)
            for ref in sorted(extra):
                typer.echo(f"  {ref}", err=True)
        raise typer.Exit(1)
    typer.echo("Lockfile is in sync.")
    raise typer.Exit(0)


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
    from ghagen.pin.collect import collect_uses_refs
    from ghagen.pin.lockfile import read_lockfile
    from ghagen.pin.resolve import ResolveError, list_tags, parse_uses, resolve_ref
    from ghagen.pin.sources import locate_uses_refs, track_user_files
    from ghagen.pin.update import apply_updates
    from ghagen.pin.versions import classify_bump, find_latest_tag, parse_tag

    if mode not in ("versions", "lockfile", "all"):
        typer.echo(
            f"Error: unknown --mode value '{mode}' "
            "(valid: versions, lockfile, all)",
            err=True,
        )
        raise typer.Exit(2)

    apply = not check

    config_path = _find_config(config)

    # Track user files during app loading (needs the import side-effects).
    user_files: set[Path] = set()
    ghagen_app_holder: list[App] = []

    def _tracked_load() -> App:
        loaded = _load_app(config_path)
        ghagen_app_holder.append(loaded)
        return loaded

    user_files = track_user_files(_tracked_load)
    ghagen_app = ghagen_app_holder[0]

    # _load_app uses exec_module which doesn't register in sys.modules,
    # so track_user_files won't see the config file itself. Add it explicitly.
    user_files.add(config_path.resolve())

    # Resolve token: flag > $GITHUB_TOKEN > $GH_TOKEN.
    gh_token = token or os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN")
    if not gh_token:
        typer.echo(
            "warning: no GitHub token found. Using unauthenticated requests "
            "(60 req/hr limit). Set $GITHUB_TOKEN or use --token.",
            err=True,
        )

    # Collect all uses: refs from the app.
    refs = collect_uses_refs(ghagen_app)

    if not refs:
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

    # Locate refs in user source files.
    ref_locations = locate_uses_refs(refs, user_files)

    # --- Version bump detection ---
    version_bumps: list[dict] = []

    check_versions = mode in ("versions", "all")
    check_lockfile = mode in ("lockfile", "all")

    if check_versions:
        # Group refs by owner/repo for efficient API calls.
        repo_refs: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for uses in sorted(refs):
            try:
                parsed = parse_uses(uses)
            except ValueError:
                continue
            key = (parsed.owner, parsed.repo)
            repo_refs.setdefault(key, []).append((uses, parsed.ref))

        # Fetch tags per repo and check for updates.
        repo_tags_cache: dict[tuple[str, str], list[str]] = {}
        for (owner, repo), uses_list in sorted(repo_refs.items()):
            if (owner, repo) not in repo_tags_cache:
                try:
                    tags = list_tags(owner, repo, token=gh_token)
                except ResolveError as exc:
                    typer.echo(
                        f"warning: failed to list tags for {owner}/{repo}: {exc}",
                        err=True,
                    )
                    continue
                repo_tags_cache[(owner, repo)] = tags

            tags = repo_tags_cache[(owner, repo)]

            for uses, current_ref in uses_list:
                latest_tag = find_latest_tag(current_ref, tags)
                if latest_tag is None:
                    continue  # up to date or non-semver

                current_ver = parse_tag(current_ref)
                latest_ver = parse_tag(latest_tag)
                if current_ver is None or latest_ver is None:
                    continue

                severity = classify_bump(current_ver, latest_ver)

                bump_entry: dict = {
                    "uses": uses,
                    "current": current_ref,
                    "latest": latest_tag,
                    "severity": severity,
                    "origin": "user",
                }
                if uses in ref_locations:
                    bump_entry["source_files"] = [
                        str(p) for p in ref_locations[uses]
                    ]
                version_bumps.append(bump_entry)

    # --- Lockfile staleness detection ---
    lockfile_stale: list[dict] = []

    if check_lockfile and ghagen_app.lockfile_path is not None:
        lockfile_full = ghagen_app.root / ghagen_app.lockfile_path
        lockfile = read_lockfile(lockfile_full)

        for uses in sorted(refs):
            entry = lockfile.get(uses)
            if entry is None:
                continue  # not pinned

            try:
                parsed = parse_uses(uses)
            except ValueError:
                continue

            try:
                current_sha = resolve_ref(
                    parsed.owner, parsed.repo, parsed.ref, token=gh_token
                )
            except ResolveError as exc:
                typer.echo(
                    f"warning: failed to resolve {uses}: {exc}",
                    err=True,
                )
                continue

            if current_sha != entry.sha:
                stale_entry: dict = {
                    "uses": uses,
                    "current_sha": entry.sha,
                    "latest_sha": current_sha,
                    "origin": "user",
                }
                if uses in ref_locations:
                    stale_entry["source_files"] = [
                        str(p) for p in ref_locations[uses]
                    ]
                lockfile_stale.append(stale_entry)

    # --- Apply updates if not in check mode ---
    if apply and version_bumps:
        updates = {
            bump["uses"]: bump["uses"].rsplit("@", 1)[0] + "@" + bump["latest"]
            for bump in version_bumps
        }
        changed_files = apply_updates(updates, ref_locations)
        if changed_files:
            typer.echo("Applied version bumps:")
            for f in changed_files:
                typer.echo(f"  modified {f}")

    # --- Output ---
    if not version_bumps and not lockfile_stale:
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
            result["version_bumps"] = version_bumps
        if check_lockfile:
            result["lockfile_stale"] = lockfile_stale
        typer.echo(json_mod.dumps(result, indent=2))
    else:
        _print_human_report(version_bumps, lockfile_stale)


def _print_human_report(
    version_bumps: list[dict],
    lockfile_stale: list[dict],
) -> None:
    """Print a human-readable upgrade report."""
    if version_bumps:
        typer.echo("Version updates available:")
        typer.echo("")
        for bump in version_bumps:
            severity_tag = f"[{bump['severity']}]"
            typer.echo(
                f"  {bump['uses']}  →  {bump['latest']}  {severity_tag}"
            )
            for src in bump.get("source_files", []):
                typer.echo(f"    in {src}")
        typer.echo("")

    if lockfile_stale:
        typer.echo("Stale lockfile entries:")
        typer.echo("")
        for entry in lockfile_stale:
            typer.echo(
                f"  {entry['uses']}"
            )
            typer.echo(
                f"    current SHA: {entry['current_sha'][:12]}..."
            )
            typer.echo(
                f"    latest SHA:  {entry['latest_sha'][:12]}..."
            )
        typer.echo("")
