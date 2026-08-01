"""Turn an :class:`~ghagen.pin.engine.UpgradeReport` into the bytes to write.

Pure: no console I/O, no CLI types, no exceptions on well-formed input.  The
CLI keeps sole ownership of *which stream* each piece of output goes to and of
exit codes (ADR-0007); this module owns *what the bytes are*.

Everything a caller used to have to know about producing ``deps upgrade``
output lives here now: the four formats and their exact bytes, the
trailing-newline discipline, the empty-report shape per format, and the
mapping from "what the engine looked for" to "which JSON keys appear".
"""

from __future__ import annotations

import json as json_mod
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from ghagen.pin.engine import LockfileStaleEntry, UpgradeReport, VersionBump

UpgradeFormat = Literal["text", "json", "pr-body", "issue-body"]
"""The output shapes :func:`render_upgrade_report` can produce."""


def render_upgrade_report(
    report: UpgradeReport, *, output_format: UpgradeFormat = "text"
) -> str:
    """Render an upgrade report, returning the exact bytes to write.

    Pure: no console I/O, no CLI types.  The returned string is already
    terminated as it should be written -- the caller writes it verbatim and
    neither adds nor suppresses a trailing newline.

    Which JSON keys appear is decided by ``report.checked_versions`` /
    ``report.checked_lockfile``, never re-derived from the CLI's ``--mode``.
    That holds for empty reports too: a run asked only for version tags emits
    only ``version_bumps``, whether or not it found any.

    Args:
        report: The typed outcome of an :func:`~ghagen.pin.engine.upgrade` run.
        output_format: One of :data:`UpgradeFormat`.  An unrecognised value is
            a programmer error -- the CLI validates ``--format`` before
            calling.

    Raises:
        ValueError: If *output_format* is not a known format.
    """
    if output_format == "json":
        return _render_json(report)
    if output_format == "pr-body":
        return _render_pr_body(report.version_bumps, report.lockfile_stale)
    if output_format == "issue-body":
        return _render_issue_body(report.version_bumps, report.lockfile_stale)
    if output_format == "text":
        return _render_text(report.version_bumps, report.lockfile_stale)
    raise ValueError(f"unknown output format {output_format!r}")


def _render_json(report: UpgradeReport) -> str:
    """Render ``--format json``, keyed by what the run was asked to check.

    Key presence follows ``checked_versions`` / ``checked_lockfile`` in *all*
    cases, empty included.  This resolves the open choice recorded in
    ``docs/specs/0005-typed-engine-report-seam.md`` Section 2.2 the other way:
    the key set now depends only on ``--mode``, which the caller chose, and not
    on whether the run happened to find anything.
    """
    result: dict = {}
    if report.checked_versions:
        result["version_bumps"] = [_bump_to_json(bump) for bump in report.version_bumps]
    if report.checked_lockfile:
        result["lockfile_stale"] = [
            _stale_to_json(entry) for entry in report.lockfile_stale
        ]
    return json_mod.dumps(result, indent=2) + "\n"


def _bump_to_json(bump: VersionBump) -> dict:
    """Serialize a version bump for ``--format json`` (omits empty ``source_files``)."""
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
    """Serialize a stale entry for ``--format json`` (omits empty ``source_files``)."""
    entry: dict = {
        "uses": stale.uses,
        "current_sha": stale.current_sha,
        "latest_sha": stale.latest_sha,
    }
    if stale.source_files:
        entry["source_files"] = list(stale.source_files)
    return entry


def _render_pr_body(
    version_bumps: list[VersionBump],
    lockfile_stale: list[LockfileStaleEntry],
) -> str:
    """Render the pull-request body markdown for an upgrade report.

    Golden-file tested against ``fixtures/expected/upgrade_pr_body.md`` and kept
    byte-identical with the TypeScript port's ``renderPrBody``.  An empty report
    yields the bare header.
    """
    lines = ["## ghagen dependency update", ""]

    if version_bumps:
        lines.append("### Version bumps")
        lines.append("")
        for bump in version_bumps:
            lines.append(f"- `{bump.uses}` -> `{bump.latest}` [{bump.severity}]")
        lines.append("")

    if lockfile_stale:
        lines.append("### Lockfile maintenance")
        lines.append("")
        for entry in lockfile_stale:
            lines.append(f"- `{entry.uses}` SHA refreshed")
        lines.append("")

    return "\n".join(lines)


def _render_issue_body(
    version_bumps: list[VersionBump],
    lockfile_stale: list[LockfileStaleEntry],
) -> str:
    """Render the issue body markdown for an upgrade report.

    Golden-file tested against ``fixtures/expected/upgrade_issue_body.md`` and
    kept byte-identical with the TypeScript port's ``renderIssueBody``.  An
    empty report yields the empty string.
    """
    lines: list[str] = []

    if version_bumps:
        lines.append("## Version updates available")
        lines.append("")
        for bump in version_bumps:
            line = f"- [ ] `{bump.uses}` -> `{bump.latest}` [{bump.severity}]"
            if bump.source_files:
                files = ", ".join(f"`{f}`" for f in bump.source_files)
                line += f"  in {files}"
            lines.append(line)
        lines.append("")

    if lockfile_stale:
        lines.append("## Stale lockfile entries")
        lines.append("")
        lines.append("Run `ghagen deps pin --update` to refresh.")
        lines.append("")
        for entry in lockfile_stale:
            lines.append(f"- [ ] `{entry.uses}` — SHA changed")
        lines.append("")

    return "\n".join(lines)


def _render_text(
    version_bumps: list[VersionBump],
    lockfile_stale: list[LockfileStaleEntry],
) -> str:
    """Render the default human-readable report.

    Golden-file tested against ``fixtures/expected/upgrade_text.txt`` and kept
    byte-identical with the TypeScript port's ``renderText``.  A report with
    nothing to say yields the up-to-date line rather than the empty string --
    this is the one format whose empty case has words in it.
    """
    lines: list[str] = []

    if version_bumps:
        lines.append("Version updates available:")
        lines.append("")
        for bump in version_bumps:
            lines.append(f"  {bump.uses}  →  {bump.latest}  [{bump.severity}]")
            for src in bump.source_files:
                lines.append(f"    in {src}")
        lines.append("")

    if lockfile_stale:
        lines.append("Stale lockfile entries:")
        lines.append("")
        for entry in lockfile_stale:
            lines.append(f"  {entry.uses}")
            lines.append(f"    current SHA: {entry.current_sha[:12]}...")
            lines.append(f"    latest SHA:  {entry.latest_sha[:12]}...")
        lines.append("")

    if not lines:
        return "Everything is up to date.\n"

    return "".join(f"{line}\n" for line in lines)
