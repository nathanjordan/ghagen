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

import json as json_mod
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Literal

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
    """Whether to write newer version tags back into the user source files.

    ``False`` whenever ``output == "issue"``: an issue reports pending work,
    it does not perform it, so no write happens for either output. See
    ``refresh_lockfile`` for the same rule applied to the lockfile.
    """

    refresh_lockfile: bool
    """Whether to re-resolve the lockfile.

    ``False`` when the App has no lockfile configured, whatever the report
    says -- ``ghagen deps pin`` exits 1 on such a project, and the report's
    ``checked_lockfile`` stays ``True`` there because it records what the run
    was *asked* for, not what it ran.  Also ``False`` whenever
    ``output == "issue"``, for the same reason as ``apply_version_bumps``.
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
            Also decides whether anything gets written: ``"issue"`` implies
            ``apply_version_bumps`` and ``refresh_lockfile`` are both
            ``False``, since an issue reports pending work rather than
            performing it.
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
    #
    # Gated on `output == "pr"`: an issue *describes* pending work, it does
    # not perform it, so `--output issue` writes nothing -- no version bumps,
    # no lockfile refresh.  This is a decision, computed the same way whether
    # or not the caller passed `--dry-run`; the CLI is what turns "would
    # apply" into "did apply" by additionally gating on `not dry_run`.
    apply_version_bumps = output == "pr" and bool(report.version_bumps)

    refresh_lockfile = (
        output == "pr"
        and app.lockfile_path is not None
        and (
            # A new version tag needs a lockfile entry whichever stage found
            # it.  This clause is deliberately *not* gated on
            # `checked_lockfile`: `--mode versions` skips the lockfile stage,
            # but it still rewrites `@v4` to `@v7` in user source, and a
            # lockfile that only knows `@v4` makes the very next `ghagen
            # synth` raise `PinError: No lockfile entry`.  `mode` is a
            # documented action input with `versions` among its values, so
            # that tree is reachable by any consumer.
            bool(report.version_bumps)
            # Read, never re-derived from `--mode`.  Load-bearing only here:
            # an empty `lockfile_stale` cannot distinguish "the stage ran and
            # found nothing" from "the stage was not asked for", so without
            # this the rule could not tell a clean lockfile from an
            # unexamined one.
            or (report.checked_lockfile and bool(report.lockfile_stale))
        )
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


PlanFormat = Literal["json", "github"]
"""The wire shapes :func:`render_update_plan` can produce."""


def render_update_plan(
    plan: UpdatePlan, *, changed: bool, output_format: PlanFormat = "github"
) -> str:
    """Render an :class:`UpdatePlan` as the exact bytes to write.

    Two encodings of one shape, built from a single mapping so a field can
    never appear in one and not the other.  As in :mod:`ghagen.pin.render`, the
    result is already terminated as it should be written: the caller writes it
    verbatim and neither adds nor suppresses a trailing newline.

    ``github`` is the ``key=value`` form appended to ``$GITHUB_OUTPUT``.  It is
    single-line per field by construction -- every value is a bool, an int, or
    a string the CLI has already rejected newlines in -- so it needs none of
    the heredoc-delimiter machinery multiline outputs require.

    Args:
        plan: The decision to serialize.
        changed: Whether the run actually wrote to the working tree.  Not a
            field of the plan: the plan is what to do, this is what happened,
            and only the caller that did it knows.
        output_format: One of :data:`PlanFormat`.  An unrecognised value is a
            programmer error -- the CLI validates ``--format`` before calling.

    Raises:
        ValueError: If *output_format* is not a known format.
    """
    fields = _plan_fields(plan, changed=changed)
    if output_format == "json":
        # ensure_ascii=False: match JSON.stringify (see pin/render.py).
        return json_mod.dumps(fields, indent=2, ensure_ascii=False) + "\n"
    if output_format == "github":
        return "".join(
            f"{key}={_github_value(value)}\n" for key, value in fields.items()
        )
    raise ValueError(f"unknown output format {output_format!r}")


def _plan_fields(plan: UpdatePlan, *, changed: bool) -> dict[str, Any]:
    """The one field list both encodings walk, in one order."""
    return {
        "action": plan.action,
        "total_updates": plan.total_updates,
        "apply_version_bumps": plan.apply_version_bumps,
        "refresh_lockfile": plan.refresh_lockfile,
        "branch": plan.branch,
        "title": plan.title,
        "commit_message": plan.commit_message,
        "labels": list(plan.labels),
        "body_format": plan.body_format,
        "changed": changed,
    }


def _github_value(value: Any) -> str:
    """Scalarize one field for a ``key=value`` line.

    ``true``/``false`` rather than Python's ``True``/``False`` because the
    consumer is a workflow ``if:`` expression, where the comparison is against
    a lowercase string literal.  ``None`` becomes empty, which is the only
    thing a composite output can be when there is no value.
    """
    if isinstance(value, bool):
        return "true" if value else "false"
    if value is None:
        return ""
    if isinstance(value, list):
        return ",".join(value)
    return str(value)
