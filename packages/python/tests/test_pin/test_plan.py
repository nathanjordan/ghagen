"""Decision-table tests for :mod:`ghagen.pin.plan`.

Offline and hermetic: every case hand-constructs an ``App`` rooted at
``tmp_path`` and an ``UpgradeReport`` literal, so nothing here can reach the
network or touch the repository's own ``.ghagen.lock.yml``.  A bare ``App()``
would resolve ``root`` to the checkout, which is exactly the accident this file
must not have.

Nothing is imported from ``test_engine.py``: the fixtures there describe how a
report is *produced*, and this module is about what a caller should *do* with
one.  The two have no shared setup and should not grow one.
"""

from __future__ import annotations

from datetime import date
from pathlib import Path

from ghagen.app import App
from ghagen.pin.engine import LockfileStaleEntry, UpgradeReport, VersionBump
from ghagen.pin.plan import UpdatePlan, plan_update, render_update_plan

_TODAY = date(2026, 7, 31)


def _bump() -> VersionBump:
    return VersionBump(
        uses="actions/checkout@v4",
        current="v4",
        latest="v6",
        severity="major",
    )


def _stale() -> LockfileStaleEntry:
    return LockfileStaleEntry(
        uses="actions/checkout@v4",
        current_sha="0" * 40,
        latest_sha="1" * 40,
    )


def _plan(app: App, report: UpgradeReport, **kwargs) -> UpdatePlan:
    """Call ``plan_update`` with the action's defaults for anything unnamed."""
    params: dict = {
        "output": "pr",
        "branch_prefix": "ghagen-update/",
        "commit_message_prefix": "",
        "labels": "",
        "today": _TODAY,
    }
    params.update(kwargs)
    return plan_update(app, report, **params)


class TestLockfileDisabled:
    """H7 — the live defect: ``lockfile=None`` is a supported configuration.

    The shipped action reconstructs "refresh the lockfile?" from a serialized
    report that deliberately does not carry ``app.lockfile_path``, so it fires
    ``deps pin --update`` on a project that has no lockfile and the command
    exits 1.  ``plan_update`` holds the ``App``, so it is the one place the
    question can be answered.
    """

    def test_version_bump_does_not_cascade_into_a_lockfile_refresh(
        self, tmp_path: Path
    ):
        app = App(root=tmp_path, lockfile=None)
        report = UpgradeReport(
            version_bumps=[_bump()],
            checked_versions=True,
            checked_lockfile=True,
        )

        plan = _plan(app, report)

        assert plan.refresh_lockfile is False
        assert plan.apply_version_bumps is True
        assert plan.action == "create-pr"
        assert plan.total_updates == 1

    def test_empty_report_is_still_nothing_to_do(self, tmp_path: Path):
        app = App(root=tmp_path, lockfile=None)
        report = UpgradeReport(checked_versions=True, checked_lockfile=True)

        plan = _plan(app, report)

        assert plan.action == "none"
        assert plan.total_updates == 0
        assert plan.refresh_lockfile is False


class TestLockfilePresent:
    """The cascade is correct when there *is* a lockfile to refresh."""

    def test_a_bump_refreshes_even_when_the_lockfile_stage_was_skipped(
        self, tmp_path: Path
    ):
        """``--mode versions`` must still leave a usable lockfile.

        This asserted the opposite until the ``--mode versions`` tree was
        found to be unsynthesizable.  Skipping the *detection* stage is not a
        reason to skip the *write*: the run still rewrote ``@v4`` to ``@v7`` in
        user source, and a lockfile that only knows ``@v4`` makes the very next
        ``ghagen synth`` raise ``PinError: No lockfile entry``.  ``mode`` is a
        documented action input with ``versions`` among its values, so that
        tree is reachable by any consumer, not just by a mistake here.
        """
        app = App(root=tmp_path)
        report = UpgradeReport(
            version_bumps=[_bump()],
            checked_versions=True,
            checked_lockfile=False,
        )

        plan = _plan(app, report)

        assert plan.refresh_lockfile is True
        assert plan.apply_version_bumps is True

    def test_a_skipped_lockfile_stage_alone_never_refreshes(self, tmp_path: Path):
        """No bumps and no lockfile stage -> nothing to write.

        The companion to the case above, and the one that keeps
        ``checked_lockfile`` load-bearing: an empty ``lockfile_stale`` cannot
        distinguish "the stage ran and found nothing" from "the stage was not
        asked for", so dropping the flag entirely would make this refresh.
        """
        app = App(root=tmp_path)
        report = UpgradeReport(checked_versions=True, checked_lockfile=False)

        plan = _plan(app, report)

        assert plan.refresh_lockfile is False
        assert plan.apply_version_bumps is False

    def test_version_bump_cascades_when_the_stage_ran(self, tmp_path: Path):
        """A bump invalidates the pinned SHA, so the cascade is right here."""
        app = App(root=tmp_path)
        report = UpgradeReport(
            version_bumps=[_bump()],
            checked_versions=True,
            checked_lockfile=True,
        )

        plan = _plan(app, report)

        assert plan.refresh_lockfile is True
        assert plan.apply_version_bumps is True

    def test_stale_entry_alone_refreshes_without_applying_bumps(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(
            lockfile_stale=[_stale()],
            checked_versions=True,
            checked_lockfile=True,
        )

        plan = _plan(app, report)

        assert plan.apply_version_bumps is False
        assert plan.refresh_lockfile is True
        assert plan.total_updates == 1


class TestAction:
    """The stage-to-action mapping and the fields it gates."""

    def test_empty_report_plans_nothing(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(checked_versions=True, checked_lockfile=True)

        plan = _plan(app, report)

        assert plan.action == "none"
        assert plan.branch == ""
        assert plan.body_format is None

    def test_pr_carries_the_dated_branch_and_the_pr_body_format(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        plan = _plan(app, report)

        assert plan.action == "create-pr"
        assert plan.branch == "ghagen-update/20260731"
        assert plan.body_format == "pr-body"
        assert plan.title == plan.commit_message

    def test_issue_has_no_branch_and_carries_the_injected_date(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        plan = _plan(app, report, output="issue")

        assert plan.action == "create-issue"
        assert plan.branch == ""
        assert plan.body_format == "issue-body"
        assert plan.title == "ghagen dependency updates available (2026-07-31)"

    def test_total_updates_sums_both_stages(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(
            version_bumps=[_bump()],
            lockfile_stale=[_stale()],
            checked_versions=True,
            checked_lockfile=True,
        )

        assert _plan(app, report).total_updates == 2


class TestOutputIssueImpliesNoWrites:
    """Issue 20: ``--output issue`` writes nothing, even with plenty to report.

    ``apply_version_bumps`` and ``refresh_lockfile`` gate the CLI's actual
    writes, so they must be ``False`` for ``output="issue"`` regardless of
    what the report found -- otherwise the plan would tell a caller "these
    were applied" for a run that applied nothing.
    """

    def test_version_bump_is_not_applied_under_issue_output(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(
            version_bumps=[_bump()],
            checked_versions=True,
            checked_lockfile=True,
        )

        plan = _plan(app, report, output="issue")

        assert plan.apply_version_bumps is False
        assert plan.refresh_lockfile is False
        assert plan.action == "create-issue"
        assert plan.total_updates == 1

    def test_stale_lockfile_entry_is_not_refreshed_under_issue_output(
        self, tmp_path: Path
    ):
        app = App(root=tmp_path)
        report = UpgradeReport(
            lockfile_stale=[_stale()],
            checked_versions=True,
            checked_lockfile=True,
        )

        plan = _plan(app, report, output="issue")

        assert plan.apply_version_bumps is False
        assert plan.refresh_lockfile is False
        assert plan.action == "create-issue"


class TestLabels:
    """The nine-line bash label loop, turned into assertions."""

    def test_labels_are_split_and_trimmed_and_blanks_dropped(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        plan = _plan(app, report, labels=" a , b ,, c ")

        assert plan.labels == ("a", "b", "c")

    def test_empty_label_input_yields_no_labels(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        assert _plan(app, report, labels="").labels == ()
        assert _plan(app, report, labels="  ,  ").labels == ()


class TestCommitMessage:
    """Prefixing, including the empty-prefix case the bash gets right."""

    def test_empty_prefix_leaves_no_leading_space(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        plan = _plan(app, report, commit_message_prefix="")

        assert plan.commit_message == "update ghagen action dependencies"

    def test_prefix_is_separated_by_one_space(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        plan = _plan(app, report, commit_message_prefix="chore(deps):")

        assert plan.commit_message == "chore(deps): update ghagen action dependencies"

    def test_prefix_is_trimmed_before_joining(self, tmp_path: Path):
        app = App(root=tmp_path)
        report = UpgradeReport(version_bumps=[_bump()], checked_versions=True)

        plan = _plan(app, report, commit_message_prefix="  chore(deps):  ")

        assert plan.commit_message == "chore(deps): update ghagen action dependencies"


class TestJsonFormatNonAscii:
    """``docs/issues/23`` item 2 also names the plan output as reachable.

    ``render_update_plan``'s ``json`` branch shares ``render_upgrade_report``'s
    ``ensure_ascii=False`` fix (see ``pin/render.py``'s golden-fixture test for
    the primary oracle); this pins the same fix at its own call site with a
    direct, byte-exact assertion rather than a fixture file, since the two
    call sites share one line of code and one rationale.
    """

    def test_json_does_not_escape_non_ascii(self, tmp_path: Path):
        plan = UpdatePlan(
            action="create-pr",
            total_updates=1,
            apply_version_bumps=True,
            refresh_lockfile=False,
            branch="ghagen-update/2026-07-31",
            title="update ghagen action dependencies",
            commit_message="update ghágen action dependencies",
            labels=(),
            body_format="pr-body",
        )

        rendered = render_update_plan(plan, changed=True, output_format="json")

        assert "ghágen" in rendered
        assert "\\u" not in rendered
