"""Decide what a caller should *do* about an :class:`UpgradeReport`.

Sibling of :mod:`ghagen.pin.render`, and the same shape of module: pure, no
network, no filesystem, no console I/O.  ``render`` answers "what bytes do I
write?"; ``plan`` answers "what do I do next?".

The distinction matters because the two questions need different inputs.  A
renderer needs only the report.  A decision needs the report **and** the
:class:`~ghagen.app.App`, because one of the three rules turns on a fact the
serialized report deliberately does not carry: whether the project has a
lockfile at all.  Any consumer that reconstructs these decisions from
``deps upgrade --format json`` is missing that fact and will get the lockfile
rule wrong -- which is exactly what the shipped ``check-deps`` action did.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from datetime import date

    from ghagen.app import App
    from ghagen.pin.engine import UpgradeReport

#: The commit subject (and PR title) an update run produces, before prefixing.
_BASE_MESSAGE = "update ghagen action dependencies"

UpdateAction = Literal["none", "create-pr", "create-issue"]
"""What the caller should raise, if anything."""

UpdateOutput = Literal["pr", "issue"]
"""Which of the two the caller asked for when there *is* something to raise."""


@dataclass(frozen=True)
class UpdatePlan:
    """What a caller should do about an :class:`UpgradeReport`.

    Every field is a decision, not data: a caller reads them and acts, and
    never re-derives one from another.  In particular ``refresh_lockfile`` is
    **not** ``bool(report.lockfile_stale)`` and cannot be computed from the
    report alone.
    """

    action: UpdateAction
    """``none`` when there is nothing to do; otherwise what to raise."""

    total_updates: int
    """Version bumps plus stale lockfile entries."""

    apply_version_bumps: bool
    """Whether to write newer version tags back into the user source files."""

    refresh_lockfile: bool
    """Whether to re-resolve the lockfile.

    ``False`` when the App has no lockfile configured, whatever the report
    says -- ``ghagen deps pin`` exits 1 on such a project, and the report's
    ``checked_lockfile`` stays ``True`` there because it records what the run
    was *asked* for, not what it ran.
    """

    branch: str
    """The dated branch to push, or ``""`` unless ``action == "create-pr"``."""

    title: str
    """The PR or issue title."""

    commit_message: str
    """The commit subject, with the caller's prefix already applied."""

    labels: tuple[str, ...]
    """Labels, already split on commas and trimmed; blanks dropped."""

    body_format: Literal["pr-body", "issue-body"] | None
    """Which :mod:`ghagen.pin.render` format to render the body in.

    ``None`` when ``action == "none"``, i.e. when there is no body to render.
    The plan carries the *format*, not the body: rendering needs the report,
    which the caller already holds, and keeping bytes off the plan is what
    lets a GitHub Actions consumer pass the body by file path rather than
    through the multiline-output delimiter dance.
    """


def plan_update(
    app: App,
    report: UpgradeReport,
    *,
    output: UpdateOutput,
    branch_prefix: str,
    commit_message_prefix: str,
    labels: str,
    today: date,
) -> UpdatePlan:
    """Decide what to do about *report*, given *app*'s configuration.

    Pure.  No network, no filesystem, no clock: *today* is injected so the
    dated branch name and issue title are testable without freezing time, the
    same reasoning ADR-0002 applies to construction-time config globals.

    Args:
        app: The loaded project.  Read for exactly one fact --
            ``app.lockfile_path`` -- which is the fact a serialized report
            cannot supply.
        report: The typed outcome of an
            :func:`~ghagen.pin.engine.upgrade` run.
        output: What the caller wants raised when there is something to raise.
        branch_prefix: Prefix for the dated PR branch, e.g. ``ghagen-update/``.
        commit_message_prefix: Optional prefix for the commit subject, e.g.
            ``chore(deps):``.  Trimmed; an empty prefix leaves no leading
            space.
        labels: Comma-separated labels, exactly as a GitHub Actions input
            hands them over.  Split and trimmed here so no caller has to.
        today: The date to stamp the branch name and issue title with.

    Returns:
        The :class:`UpdatePlan` for this report.
    """
    total_updates = len(report.version_bumps) + len(report.lockfile_stale)

    # No `mode` reference anywhere in this function.  `upgrade()` guarantees
    # `version_bumps` is empty unless the versions stage ran, so the flag adds
    # nothing here -- reading it would make this a fresh derivation site for a
    # fact the report already encodes structurally.
    apply_version_bumps = bool(report.version_bumps)

    refresh_lockfile = (
        # The fact the payload drops: `deps pin` exits 1 on a project with no
        # lockfile, so a cascade into it is not "harmless extra work".
        app.lockfile_path is not None
        # Read, never re-derived from `--mode`.  Load-bearing only in this
        # rule: an empty `lockfile_stale` cannot distinguish "the stage ran
        # and found nothing" from "the stage was not asked for", and the
        # cascade clause below fires on version bumps alone.
        and report.checked_lockfile
        and (bool(report.lockfile_stale) or apply_version_bumps)
    )

    if total_updates == 0:
        action: UpdateAction = "none"
    elif output == "pr":
        action = "create-pr"
    else:
        action = "create-issue"

    prefix = commit_message_prefix.strip()
    commit_message = f"{prefix} {_BASE_MESSAGE}" if prefix else _BASE_MESSAGE

    if output == "pr":
        title = commit_message
    else:
        title = f"ghagen dependency updates available ({today:%Y-%m-%d})"

    body_format: Literal["pr-body", "issue-body"] | None
    if action == "create-pr":
        body_format = "pr-body"
    elif action == "create-issue":
        body_format = "issue-body"
    else:
        body_format = None

    return UpdatePlan(
        action=action,
        total_updates=total_updates,
        apply_version_bumps=apply_version_bumps,
        refresh_lockfile=refresh_lockfile,
        branch=f"{branch_prefix}{today:%Y%m%d}" if action == "create-pr" else "",
        title=title,
        commit_message=commit_message,
        labels=parse_labels(labels),
        body_format=body_format,
    )


def parse_labels(labels: str) -> tuple[str, ...]:
    """Split a comma-separated label input, trimming and dropping blanks.

    Exposed because it is the whole of what a caller would otherwise reproduce
    in shell, and because ``plan_update``'s ``labels`` field is the only place
    the result is observable.
    """
    return tuple(part.strip() for part in labels.split(",") if part.strip())
