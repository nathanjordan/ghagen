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

import json
from datetime import date
from pathlib import Path

from ruamel.yaml import YAML

from ghagen.app import App
from ghagen.pin.engine import LockfileStaleEntry, UpgradeReport, VersionBump
from ghagen.pin.plan import UpdatePlan, plan_update, render_update_plan
from ghagen_schema.paths import EXPECTED_DIR, SCHEMA_DIR

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


# ---------------------------------------------------------------------------
# The shared plan-field table: order, type, and encoding
# ---------------------------------------------------------------------------

#: ``schema/update-plan-fields.yml``, whole -- names, order, JSON type, and
#: ``$GITHUB_OUTPUT`` encoding, one row per field.
#:
#: The name and order axes are also driven from ``tests/test_cli/test_deps.py``
#: against a live invocation.  The type and encoding axes are driven here
#: instead, because they need *two* plans -- one with ``action == "none"`` and
#: one without -- to say anything about ``body_format``'s conditional null, and
#: an ``action == "none"`` run is not reachable from the CLI suite's fixtures
#: without a second mocked project.  ``plan_update`` is pure, so both are one
#: line each here.
#:
#: The TypeScript mirror is ``src/pin/plan.test.ts``; corrupting one row of the
#: shared file fails both.
_FIELD_TABLE: list[dict] = YAML(typ="safe").load(
    (SCHEMA_DIR / "update-plan-fields.yml").read_text()
)["fields"]

assert _FIELD_TABLE, (
    "schema/update-plan-fields.yml carries no fields -- every case below "
    "would be vacuous"
)


def _json_type_holds(value: object, declared: str) -> bool:
    """Whether *value* is the JSON type the table declares."""
    if declared == "string":
        return isinstance(value, str)
    if declared == "integer":
        # ``not isinstance(value, bool)``: ``bool`` is a subclass of ``int`` in
        # Python, so without this every boolean field would also pass as an
        # integer and the two rows would be indistinguishable.
        return isinstance(value, int) and not isinstance(value, bool)
    if declared == "boolean":
        return isinstance(value, bool)
    if declared == "string-array":
        return isinstance(value, list) and all(isinstance(x, str) for x in value)
    raise AssertionError(f"unknown json type {declared!r} in the shared table")


def _github_encode(value: object, encoding: str) -> str:
    """The ``key=`` right-hand side the table's *encoding* rule demands."""
    if value is None:
        return ""
    if encoding == "verbatim":
        assert isinstance(value, str)
        return value
    if encoding == "decimal":
        return str(value)
    if encoding == "lowercase-bool":
        return "true" if value else "false"
    if encoding == "comma-joined":
        assert isinstance(value, list)
        return ",".join(value)
    raise AssertionError(f"unknown github encoding {encoding!r} in the shared table")


def _github_pairs(rendered: str) -> dict[str, str]:
    """Parse a ``--format github`` render back into ``key -> value``."""
    return dict(line.split("=", 1) for line in rendered.splitlines())


def _both_encodings(plan: UpdatePlan, *, changed: bool):
    """``(json document, github key=value mapping)`` for one plan."""
    return (
        json.loads(render_update_plan(plan, changed=changed, output_format="json")),
        _github_pairs(
            render_update_plan(plan, changed=changed, output_format="github")
        ),
    )


class TestSharedFieldTable:
    """``schema/update-plan-fields.yml``, held to all three of its axes.

    Gap 1 of docs/issues/33: the shared file bound field *names* and nothing
    else, so two ports emitting the same ten fields in two different orders, or
    encoding ``labels`` as a list in one port and a comma-joined string in the
    other, were both invisible to it.
    """

    def _pr_plan(self, tmp_path: Path) -> UpdatePlan:
        """A plan with every field at a non-degenerate value."""
        return _plan(
            App(root=tmp_path),
            UpgradeReport(
                version_bumps=[_bump()],
                lockfile_stale=[_stale()],
                checked_versions=True,
                checked_lockfile=True,
            ),
            commit_message_prefix="chore(deps):",
            labels=" ci , deps ,, automated ",
        )

    def _none_plan(self, tmp_path: Path) -> UpdatePlan:
        """The one plan whose ``body_format`` is null."""
        return _plan(
            App(root=tmp_path),
            UpgradeReport(checked_versions=True, checked_lockfile=True),
        )

    def test_both_encodings_carry_the_table_s_fields_in_the_table_s_order(
        self, tmp_path: Path
    ):
        """Order, not just membership -- the axis a set comparison cannot see."""
        names = [field["name"] for field in _FIELD_TABLE]

        for plan in (self._pr_plan(tmp_path), self._none_plan(tmp_path)):
            as_json, as_github = _both_encodings(plan, changed=True)
            assert list(as_json) == names
            assert list(as_github) == names

    def test_every_field_has_the_declared_json_type(self, tmp_path: Path):
        for plan in (self._pr_plan(tmp_path), self._none_plan(tmp_path)):
            as_json, _ = _both_encodings(plan, changed=True)
            for field in _FIELD_TABLE:
                value = as_json[field["name"]]
                if value is None:
                    # Legality of the null itself is the biconditional below.
                    continue
                assert _json_type_holds(value, field["json"]), (
                    f"{field['name']}: {value!r} is not {field['json']}"
                )

    def test_every_field_encodes_into_github_the_declared_way(self, tmp_path: Path):
        """``labels`` is a JSON array and a comma-joined string. So says the table."""
        for plan in (self._pr_plan(tmp_path), self._none_plan(tmp_path)):
            as_json, as_github = _both_encodings(plan, changed=True)
            for field in _FIELD_TABLE:
                name = field["name"]
                assert as_github[name] == _github_encode(
                    as_json[name], field["github"]
                ), name

    def test_labels_really_does_differ_between_the_two_encodings(self, tmp_path: Path):
        """The row above passes vacuously if no field exercises the difference."""
        as_json, as_github = _both_encodings(self._pr_plan(tmp_path), changed=True)

        assert as_json["labels"] == ["ci", "deps", "automated"]
        assert as_github["labels"] == "ci,deps,automated"

    def test_null_holds_exactly_where_the_table_says_it_does(self, tmp_path: Path):
        """A biconditional, in both encodings, over both plans.

        ``body_format`` carries ``null_when: {field: action, equals: none}``;
        every other row carries no ``null_when`` at all and is therefore never
        null.  Asserting the "only when" half is what stops a port from
        nulling ``body_format`` on some other condition -- say on
        ``--output issue`` -- and still passing.
        """
        for plan in (self._pr_plan(tmp_path), self._none_plan(tmp_path)):
            as_json, as_github = _both_encodings(plan, changed=True)
            for field in _FIELD_TABLE:
                name = field["name"]
                rule = field.get("null_when")
                expected_null = (
                    rule is not None and as_json[rule["field"]] == rule["equals"]
                )
                assert (as_json[name] is None) is expected_null, name
                # A null renders as the empty string on the github side.  Only
                # the forward direction: `branch` is legitimately `""` under
                # `action: none` without being null, so emptiness there is not
                # evidence of a null.  The converse is covered by
                # `test_every_field_encodes_into_github_the_declared_way`,
                # which pins every field's github form to its JSON value.
                if expected_null:
                    assert as_github[name] == "", name


class TestGoldenRenders:
    """``fixtures/expected/update_plan{.json,_github.txt}`` -- byte for byte.

    The table above binds the shape; these bind the bytes, and they are the
    fixtures docs/issues/33 Gap 1 names.  What they add over the table is the
    serialization detail the table has no vocabulary for: the two-space JSON
    indent, the one-element-per-line array, the trailing newline on both
    renders, and the literal ``key=value`` line form -- all of it shared with
    the TypeScript port, whose ``src/pin/plan.test.ts`` reads the same two
    files and compares the same way.
    """

    def _golden_plan(self, tmp_path: Path) -> UpdatePlan:
        return _plan(
            App(root=tmp_path),
            UpgradeReport(
                version_bumps=[_bump()],
                lockfile_stale=[_stale()],
                checked_versions=True,
                checked_lockfile=True,
            ),
            commit_message_prefix="chore(deps):",
            labels=" ci , deps ,, automated ",
        )

    def test_json_render_matches_the_golden(self, tmp_path: Path):
        rendered = render_update_plan(
            self._golden_plan(tmp_path), changed=True, output_format="json"
        )

        assert rendered == (EXPECTED_DIR / "update_plan.json").read_text(
            encoding="utf-8"
        )

    def test_github_render_matches_the_golden(self, tmp_path: Path):
        rendered = render_update_plan(
            self._golden_plan(tmp_path), changed=True, output_format="github"
        )

        assert rendered == (EXPECTED_DIR / "update_plan_github.txt").read_text(
            encoding="utf-8"
        )
