"""Pin engine — pin / check-sync / upgrade orchestration returning typed reports.

The engine lifts the pin/upgrade/check-synced logic out of the CLI handlers so
that it is unit-testable without a Typer runner.  Each function takes the loaded
:class:`~ghagen.app.App` (and, for the networked operations, an injected
:class:`~ghagen.pin.github.GitHubClient`) and returns a typed report.  The
engine performs its own side effects — writing the lockfile in :func:`pin`,
mutating source files in :func:`upgrade` when ``apply=True`` — but does **no**
console I/O: human-facing messages are collected into ``report.warnings`` /
``report.errors`` for the CLI to render.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ghagen.pin.collect import collect_uses_refs
from ghagen.pin.github import ResolveError
from ghagen.pin.lockfile import PinEntry, read_lockfile, write_lockfile
from ghagen.pin.sources import locate_uses_refs
from ghagen.pin.update import apply_updates
from ghagen.pin.uses import UsesRef
from ghagen.pin.versions import classify_bump, find_latest_tag, parse_tag

if TYPE_CHECKING:
    from ghagen.app import App
    from ghagen.pin.github import GitHubClient

Severity = Literal["major", "minor", "patch"]


# -- pin -------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedPin:
    """A single ``uses:`` ref newly resolved to a commit SHA."""

    uses: str
    sha: str


@dataclass
class PinReport:
    """Outcome of a :func:`pin` run."""

    resolved: list[ResolvedPin] = field(default_factory=list)
    """Refs newly resolved to SHAs (in sorted processing order)."""

    errors: list[str] = field(default_factory=list)
    """Human messages for refs that failed to resolve (``"uses: reason"``)."""

    warnings: list[str] = field(default_factory=list)
    """Non-fatal warnings (e.g. a ref skipped as unpinnable)."""

    pruned: int = 0
    """Number of stale entries removed from the lockfile."""

    written: bool = False
    """Whether the lockfile was written to disk."""

    lockfile_path: Path | None = None
    """Absolute path of the lockfile the report targets."""

    up_to_date: bool = False
    """True when nothing needed resolving and nothing was pruned."""


def pin(
    app: App,
    client: GitHubClient,
    *,
    update: bool,
    prune: bool,
) -> PinReport:
    """Resolve ``uses:`` refs to commit SHAs and merge them into the lockfile.

    By default only unpinned refs are resolved; ``update`` re-resolves all of
    them.  Stale entries no longer referenced in code are pruned when *prune*
    is set.  The lockfile is written when anything changed.
    """
    lockfile_path = app.lockfile_path
    if lockfile_path is None:
        raise ValueError("pin(): app has no lockfile (lockfile=None)")
    lockfile_full = app.root / lockfile_path

    report = PinReport(lockfile_path=lockfile_full)

    refs = collect_uses_refs(app)
    lockfile = read_lockfile(lockfile_full)

    to_resolve = refs if update else refs - set(lockfile.keys())

    now = datetime.now(UTC)
    for uses in sorted(to_resolve):
        parsed = UsesRef.parse(uses)
        if parsed is None:
            report.warnings.append(
                f"skipping {uses!r}: not a pinnable action reference"
            )
            continue
        try:
            sha = client.resolve_ref(parsed.owner, parsed.repo, parsed.ref)
        except ResolveError as exc:
            report.errors.append(f"{uses}: {exc}")
            continue
        lockfile.set(uses, PinEntry(sha=sha, resolved_at=now))
        report.resolved.append(ResolvedPin(uses=uses, sha=sha))

    if prune:
        report.pruned = lockfile.prune(refs)

    if report.resolved or report.pruned:
        write_lockfile(lockfile, lockfile_full)
        report.written = True

    report.up_to_date = not to_resolve and not report.pruned
    return report


# -- check-sync ------------------------------------------------------------


@dataclass
class SyncReport:
    """Outcome of a :func:`check_sync` run (sorted lists)."""

    missing: list[str] = field(default_factory=list)
    """Refs referenced in code but absent from the lockfile."""

    extra: list[str] = field(default_factory=list)
    """Lockfile entries no longer referenced in code (empty when not pruning)."""

    @property
    def in_sync(self) -> bool:
        """True when there is nothing missing and nothing extra."""
        return not self.missing and not self.extra


def check_sync(app: App, *, prune: bool) -> SyncReport:
    """Compare the lockfile against the app's refs — pure, no network.

    Returns the sorted ``missing`` / ``extra`` sets.  ``extra`` is only
    computed when *prune* is set (matching the CLI's ``--no-prune``).
    """
    lockfile_path = app.lockfile_path
    if lockfile_path is None:
        raise ValueError("check_sync(): app has no lockfile (lockfile=None)")
    lockfile_full = app.root / lockfile_path

    refs = collect_uses_refs(app)
    lockfile = read_lockfile(lockfile_full)
    keys = set(lockfile.keys())

    missing = sorted(refs - keys)
    extra = sorted(keys - refs) if prune else []
    return SyncReport(missing=missing, extra=extra)


# -- upgrade ---------------------------------------------------------------


@dataclass(frozen=True)
class VersionBump:
    """A newer version tag available for a ``uses:`` ref."""

    uses: str
    current: str
    latest: str
    severity: Severity
    source_files: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class LockfileStaleEntry:
    """A pinned ref whose lockfile SHA no longer matches its ref."""

    uses: str
    current_sha: str
    latest_sha: str
    source_files: list[str] = field(default_factory=list)


@dataclass
class UpgradeReport:
    """Outcome of an :func:`upgrade` run."""

    version_bumps: list[VersionBump] = field(default_factory=list)
    lockfile_stale: list[LockfileStaleEntry] = field(default_factory=list)
    changed_files: list[Path] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


def upgrade(
    app: App,
    client: GitHubClient,
    user_files: set[Path],
    *,
    mode: Literal["versions", "lockfile", "all"],
    apply: bool,
) -> UpgradeReport:
    """Detect available upgrades and optionally apply version bumps.

    Depending on *mode*, detects newer version tags (``versions``), stale
    lockfile SHAs (``lockfile``), or both (``all``).  When *apply* is set,
    version bumps are written back into the user source files identified by
    *user_files*; the changed files are recorded on the report.
    """
    report = UpgradeReport()

    refs = collect_uses_refs(app)
    if not refs:
        return report

    ref_locations = locate_uses_refs(refs, user_files)

    check_versions = mode in ("versions", "all")
    check_lockfile = mode in ("lockfile", "all")

    if check_versions:
        # Group refs by owner/repo for efficient API calls.
        repo_refs: dict[tuple[str, str], list[tuple[str, str]]] = {}
        for uses in sorted(refs):
            parsed = UsesRef.parse(uses)
            if parsed is None:
                continue
            repo_refs.setdefault((parsed.owner, parsed.repo), []).append(
                (uses, parsed.ref)
            )

        # Per-repo tag cache stays engine-local.
        repo_tags_cache: dict[tuple[str, str], list[str]] = {}
        for (owner, repo), uses_list in sorted(repo_refs.items()):
            if (owner, repo) not in repo_tags_cache:
                try:
                    tags = client.list_tags(owner, repo)
                except ResolveError as exc:
                    report.warnings.append(
                        f"failed to list tags for {owner}/{repo}: {exc}"
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

                severity = classify_bump(current_ver.version, latest_ver.version)
                report.version_bumps.append(
                    VersionBump(
                        uses=uses,
                        current=current_ref,
                        latest=latest_tag,
                        severity=severity,
                        source_files=[str(p) for p in ref_locations.get(uses, [])],
                    )
                )

    if check_lockfile and app.lockfile_path is not None:
        lockfile_full = app.root / app.lockfile_path
        lockfile = read_lockfile(lockfile_full)

        for uses in sorted(refs):
            entry = lockfile.get(uses)
            if entry is None:
                continue  # not pinned

            parsed = UsesRef.parse(uses)
            if parsed is None:
                continue

            try:
                current_sha = client.resolve_ref(parsed.owner, parsed.repo, parsed.ref)
            except ResolveError as exc:
                report.warnings.append(f"failed to resolve {uses}: {exc}")
                continue

            if current_sha != entry.sha:
                report.lockfile_stale.append(
                    LockfileStaleEntry(
                        uses=uses,
                        current_sha=entry.sha,
                        latest_sha=current_sha,
                        source_files=[str(p) for p in ref_locations.get(uses, [])],
                    )
                )

    if apply and report.version_bumps:
        updates: dict[str, str] = {}
        for bump in report.version_bumps:
            parsed = UsesRef.parse(bump.uses)
            if parsed is None:
                continue
            updates[bump.uses] = parsed.with_sha(bump.latest)
        report.changed_files = apply_updates(updates, ref_locations)

    return report
