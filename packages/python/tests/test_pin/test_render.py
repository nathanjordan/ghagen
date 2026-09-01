"""Unit tests for :mod:`ghagen.pin.render` -- no ``CliRunner``, no command.

These assertions used to live in ``tests/test_cli/test_deps.py`` and reach the
renderers only by spinning up a temp project and driving a Typer command.  The
renderer is a pure function from a typed report to a string, so it is tested as
one.  See ``docs/specs/0005-typed-engine-report-seam.md`` Part A.

The four format goldens in ``fixtures/expected/`` are byte-compared by both
ports; ``upgrade_text.txt`` is new in proposal 17 and is the first cross-port
oracle the default human-readable format has ever had.
"""

from __future__ import annotations

import json

import pytest

from ghagen.pin.engine import LockfileStaleEntry, UpgradeReport, VersionBump
from ghagen.pin.render import render_upgrade_report
from ghagen_schema.paths import FIXTURES_DIR as _FIXTURES_ROOT

FIXTURES_DIR = _FIXTURES_ROOT / "expected"


def _bumps() -> list[VersionBump]:
    """The shared golden's version bumps (the second has no source files)."""
    return [
        VersionBump(
            uses="actions/checkout@v5",
            current="v5",
            latest="v6",
            severity="major",
            source_files=[".github/ghagen_workflows.py"],
        ),
        VersionBump(
            uses="actions/setup-node@v3",
            current="v3",
            latest="v4",
            severity="major",
            source_files=[],
        ),
    ]


def _stale() -> list[LockfileStaleEntry]:
    """The shared golden's stale lockfile entry."""
    return [
        LockfileStaleEntry(
            uses="actions/setup-python@v6",
            current_sha="ece7cb06caefa5fff74198d8649806c4678c61a1",
            latest_sha="aaaa1111bbbb2222cccc3333dddd4444eeee5555",
            source_files=[".github/ghagen_workflows.py"],
        )
    ]


def _full_report(**overrides: object) -> UpgradeReport:
    """A report carrying the shared golden data, both stages asked for."""
    kwargs: dict = {
        "version_bumps": _bumps(),
        "lockfile_stale": _stale(),
        "checked_versions": True,
        "checked_lockfile": True,
    }
    kwargs.update(overrides)
    return UpgradeReport(**kwargs)  # type: ignore[arg-type]


# -- goldens ---------------------------------------------------------------


class TestGoldenFixtures:
    """Every format is byte-compared against the shared cross-port oracle."""

    def test_json_matches_golden_fixture(self):
        rendered = render_upgrade_report(_full_report(), output_format="json")

        golden = (FIXTURES_DIR / "upgrade_report.json").read_text(encoding="utf-8")
        assert json.loads(rendered) == json.loads(golden)

        # The phantom `helper_provided` field must never appear.
        assert "helper_provided" not in rendered

    def test_pr_body_matches_golden_fixture(self):
        assert render_upgrade_report(_full_report(), output_format="pr-body") == (
            FIXTURES_DIR / "upgrade_pr_body.md"
        ).read_text(encoding="utf-8")

    def test_issue_body_matches_golden_fixture(self):
        assert render_upgrade_report(_full_report(), output_format="issue-body") == (
            FIXTURES_DIR / "upgrade_issue_body.md"
        ).read_text(encoding="utf-8")

    def test_text_matches_golden_fixture(self):
        """The default format's first direct test in either port."""
        assert render_upgrade_report(_full_report(), output_format="text") == (
            FIXTURES_DIR / "upgrade_text.txt"
        ).read_text(encoding="utf-8")

    def test_text_is_the_default_format(self):
        report = _full_report()
        assert render_upgrade_report(report) == render_upgrade_report(
            report, output_format="text"
        )


# -- the JSON key set ------------------------------------------------------


class TestJsonKeySet:
    """Key presence follows ``checked_*``, never the data, never ``--mode``."""

    def test_source_files_omitted_when_empty(self):
        report = UpgradeReport(
            version_bumps=[
                VersionBump(
                    uses="actions/setup-node@v3",
                    current="v3",
                    latest="v4",
                    severity="major",
                    source_files=[],
                )
            ],
            lockfile_stale=[
                LockfileStaleEntry(
                    uses="actions/setup-python@v6",
                    current_sha="a" * 40,
                    latest_sha="b" * 40,
                    source_files=[],
                )
            ],
            checked_versions=True,
            checked_lockfile=True,
        )

        data = json.loads(render_upgrade_report(report, output_format="json"))

        assert "source_files" not in data["version_bumps"][0]
        assert "source_files" not in data["lockfile_stale"][0]

    def test_checked_versions_only_omits_lockfile_stale_key(self):
        report = _full_report(checked_versions=True, checked_lockfile=False)

        data = json.loads(render_upgrade_report(report, output_format="json"))

        assert "version_bumps" in data
        assert "lockfile_stale" not in data

    def test_checked_lockfile_only_omits_version_bumps_key(self):
        report = _full_report(checked_versions=False, checked_lockfile=True)

        data = json.loads(render_upgrade_report(report, output_format="json"))

        assert "lockfile_stale" in data
        assert "version_bumps" not in data

    @pytest.mark.parametrize(
        ("checked_versions", "checked_lockfile", "expected"),
        [
            (True, False, {"version_bumps": []}),
            (False, True, {"lockfile_stale": []}),
            (True, True, {"version_bumps": [], "lockfile_stale": []}),
        ],
    )
    def test_empty_report_emits_only_the_keys_it_checked(
        self, checked_versions: bool, checked_lockfile: bool, expected: dict
    ):
        """An *empty* report obeys the same rule as a non-empty one.

        This inverts the behaviour ``test_deps.py`` used to pin, and resolves
        the open choice recorded in
        ``docs/specs/0005-typed-engine-report-seam.md`` Section 2.2: the empty
        case no longer hard-codes both keys.  The key set now depends only on
        ``--mode``, which the caller chose, instead of on data the caller
        cannot predict.
        """
        report = UpgradeReport(
            checked_versions=checked_versions, checked_lockfile=checked_lockfile
        )

        rendered = render_upgrade_report(report, output_format="json")

        assert json.loads(rendered) == expected
        assert "helper_provided" not in rendered

    def test_no_keys_checked_renders_an_empty_object(self):
        assert render_upgrade_report(UpgradeReport(), output_format="json") == "{}\n"


# -- the empty report, per format ------------------------------------------


class TestEmptyReport:
    """Empty is not a separate code path -- it is the same branch, no data."""

    def test_text_says_everything_is_up_to_date(self):
        assert (
            render_upgrade_report(UpgradeReport(), output_format="text")
            == "Everything is up to date.\n"
        )

    def test_pr_body_is_the_bare_header(self):
        assert (
            render_upgrade_report(UpgradeReport(), output_format="pr-body")
            == "## ghagen dependency update\n"
        )

    def test_issue_body_is_empty(self):
        assert render_upgrade_report(UpgradeReport(), output_format="issue-body") == ""


# -- the interface ---------------------------------------------------------


class TestInterface:
    def test_every_format_is_terminated_as_written(self):
        """The caller writes the result verbatim, so it must self-terminate."""
        report = _full_report()
        for output_format in ("text", "json", "pr-body", "issue-body"):
            rendered = render_upgrade_report(report, output_format=output_format)  # type: ignore[arg-type]
            assert rendered.endswith("\n"), output_format
            assert not rendered.endswith("\n\n\n"), output_format

    def test_unknown_format_is_a_programmer_error(self):
        with pytest.raises(ValueError, match="unknown output format"):
            render_upgrade_report(UpgradeReport(), output_format="yaml")  # type: ignore[arg-type]

    def test_renders_without_touching_the_report(self):
        """Pure: rendering must not mutate its input."""
        report = _full_report()
        before = (len(report.version_bumps), len(report.lockfile_stale))

        for output_format in ("text", "json", "pr-body", "issue-body"):
            render_upgrade_report(report, output_format=output_format)  # type: ignore[arg-type]

        assert (len(report.version_bumps), len(report.lockfile_stale)) == before
