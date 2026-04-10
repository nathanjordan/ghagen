"""ghagen CLI — generate GitHub Actions workflows from Python."""

from __future__ import annotations

import importlib.util
import json as json_mod
import os
import sys
import tomllib
from datetime import UTC, datetime
from pathlib import Path

import typer

from ghagen.app import App
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
                f"{meta.id} ({meta.default_severity.value})\n"
                f"  {meta.description}"
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
            f"Error: unknown --format value '{format}' "
            "(valid: human, json, github)",
            err=True,
        )
        raise typer.Exit(2)

    # Exit 1 only if there are error-severity violations
    if any(v.severity == Severity.ERROR for v in violations):
        raise typer.Exit(1)


@app.command()
def pin(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    update: bool = typer.Option(
        False, "--update", help="Re-resolve all entries to latest SHAs"
    ),
    check_mode: bool = typer.Option(
        False,
        "--check",
        help="Verify lockfile is in sync with code (exit 1 if stale)",
    ),
    prune: bool = typer.Option(
        False, "--prune", help="Remove lockfile entries not referenced in code"
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

    if check_mode:
        # --check: verify lockfile covers all refs and nothing is stale.
        # No network calls here, so no token is required.
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

    # Resolve token: flag > $GITHUB_TOKEN > $GH_TOKEN. Only the resolve path
    # below needs a token; --check returned above.
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


@app.command()
def outdated(
    config: str | None = typer.Option(
        None, "--config", "-c", help="Path to config file"
    ),
    json: bool = typer.Option(
        False, "--json", help="Output in machine-readable JSON format"
    ),
    mode: str = typer.Option(
        "all",
        "--mode",
        help="Detection mode: 'versions', 'lockfile', or 'all' (default)",
    ),
    apply: bool = typer.Option(
        False, "--apply", help="Apply version bump changes to source files"
    ),
    token: str | None = typer.Option(
        None, "--token", help="GitHub token (default: $GITHUB_TOKEN)"
    ),
) -> None:
    """Check for outdated action references and stale lockfile entries."""
    from ghagen.pin.collect import collect_uses_refs
    from ghagen.pin.lockfile import read_lockfile
    from ghagen.pin.resolve import ResolveError, list_tags, parse_uses, resolve_ref
    from ghagen.pin.sources import classify_refs, locate_uses_refs, track_user_files
    from ghagen.pin.update import apply_updates
    from ghagen.pin.versions import classify_bump, find_latest_tag, parse_tag

    if mode not in ("versions", "lockfile", "all"):
        typer.echo(
            f"Error: unknown --mode value '{mode}' "
            "(valid: versions, lockfile, all)",
            err=True,
        )
        raise typer.Exit(2)

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
                    {"version_bumps": [], "lockfile_stale": [], "helper_provided": []},
                    indent=2,
                )
            )
        else:
            typer.echo("Everything is up to date.")
        raise typer.Exit(0)

    # Classify refs into user-controlled vs helper-provided.
    ref_locations = locate_uses_refs(refs, user_files)
    user_refs, helper_refs = classify_refs(refs, ref_locations)

    # --- Version bump detection ---
    version_bumps: list[dict] = []
    helper_provided: list[dict] = []

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

                if uses in user_refs:
                    version_bumps.append(
                        {
                            "uses": uses,
                            "current": current_ref,
                            "latest": latest_tag,
                            "severity": severity,
                            "origin": "user",
                            "source_files": [
                                str(p) for p in user_refs[uses]
                            ],
                        }
                    )
                elif uses in helper_refs:
                    helper_provided.append(
                        {
                            "uses": uses,
                            "current": current_ref,
                            "latest": latest_tag,
                            "severity": severity,
                            "helper": "ghagen built-in",
                        }
                    )

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
                origin = "user" if uses in user_refs else "helper"
                stale_entry: dict = {
                    "uses": uses,
                    "current_sha": entry.sha,
                    "latest_sha": current_sha,
                    "origin": origin,
                }
                if uses in user_refs:
                    stale_entry["source_files"] = [
                        str(p) for p in user_refs[uses]
                    ]
                lockfile_stale.append(stale_entry)

    # --- Apply updates if requested ---
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
    if not version_bumps and not lockfile_stale and not helper_provided:
        if json:
            typer.echo(
                json_mod.dumps(
                    {"version_bumps": [], "lockfile_stale": [], "helper_provided": []},
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
        if check_versions:
            result["helper_provided"] = helper_provided
        typer.echo(json_mod.dumps(result, indent=2))
    else:
        _print_human_report(version_bumps, lockfile_stale, helper_provided)


def _print_human_report(
    version_bumps: list[dict],
    lockfile_stale: list[dict],
    helper_provided: list[dict],
) -> None:
    """Print a human-readable outdated report."""
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

    if helper_provided:
        typer.echo("Helper-provided action updates:")
        typer.echo("")
        for hp in helper_provided:
            severity_tag = f"[{hp['severity']}]"
            typer.echo(
                f"  {hp['uses']}  →  {hp['latest']}  {severity_tag}"
            )
            typer.echo(f"    provided by: {hp['helper']}")
        typer.echo("")
