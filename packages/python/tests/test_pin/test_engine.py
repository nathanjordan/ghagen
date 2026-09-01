"""Unit tests for the pin engine (pin / check_sync / upgrade).

``check_sync`` needs no client at all; ``pin`` and ``upgrade`` are driven
through a :class:`GitHubClient` backed by a canned ``FakeTransport`` (no
network) plus tmp dirs.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ghagen.app import App
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.engine import check_sync, pin, upgrade
from ghagen.pin.github import GitHubClient, Response
from ghagen.pin.lockfile import Lockfile, PinEntry, read_lockfile, write_lockfile
from ghagen_schema.paths import EXPECTED_DIR
from tests.test_pin.transport_contract import FakeTransport, canned

SAMPLE_TIME = datetime(2026, 4, 9, tzinfo=UTC)


def _app_with_refs(root: Path, *uses: str) -> App:
    """Build an App with a single workflow whose steps carry *uses* refs."""
    app = App(root=root)
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(uses=u) for u in uses],
            )
        },
    )
    app.add_workflow(wf, "ci.yml")
    return app


def _app_without_refs(root: Path) -> App:
    """Build an App whose only step is a ``run:`` — no pinnable ``uses`` refs."""
    app = App(root=root)
    wf = Workflow(
        name="CI",
        on=On(push=PushTrigger(branches=["main"])),
        jobs={
            "test": Job(
                runs_on="ubuntu-latest",
                steps=[Step(name="Test", run="echo hi")],
            )
        },
    )
    app.add_workflow(wf, "ci.yml")
    return app


def _write_lockfile(root: Path, **pins: str) -> Path:
    lf = Lockfile(
        pins={u: PinEntry(sha=sha, resolved_at=SAMPLE_TIME) for u, sha in pins.items()}
    )
    path = root / ".ghagen.lock.yml"
    write_lockfile(lf, path)
    return path


def _commit(sha: str) -> Response:
    return canned({"object": {"type": "commit", "sha": sha}})


def _tags(*names: str) -> Response:
    return canned([{"ref": f"refs/tags/{n}"} for n in names])


# -- check_sync (no client) ------------------------------------------------


class TestCheckSync:
    def test_in_sync(self, tmp_path: Path):
        _write_lockfile(tmp_path, **{"actions/checkout@v4": "a" * 40})
        app = _app_with_refs(tmp_path, "actions/checkout@v4")

        report = check_sync(app, prune=True)

        assert report.in_sync
        assert report.missing == []
        assert report.extra == []

    def test_missing(self, tmp_path: Path):
        _write_lockfile(tmp_path)  # empty lockfile
        app = _app_with_refs(tmp_path, "actions/checkout@v4")

        report = check_sync(app, prune=True)

        assert not report.in_sync
        assert report.missing == ["actions/checkout@v4"]
        assert report.extra == []

    def test_extra(self, tmp_path: Path):
        _write_lockfile(
            tmp_path,
            **{
                "actions/checkout@v4": "a" * 40,
                "actions/stale@v1": "b" * 40,
            },
        )
        app = _app_with_refs(tmp_path, "actions/checkout@v4")

        report = check_sync(app, prune=True)

        assert not report.in_sync
        assert report.missing == []
        assert report.extra == ["actions/stale@v1"]

    def test_extra_ignored_without_prune(self, tmp_path: Path):
        _write_lockfile(
            tmp_path,
            **{
                "actions/checkout@v4": "a" * 40,
                "actions/stale@v1": "b" * 40,
            },
        )
        app = _app_with_refs(tmp_path, "actions/checkout@v4")

        report = check_sync(app, prune=False)

        assert report.in_sync
        assert report.extra == []


# -- pin -------------------------------------------------------------------


class TestPin:
    def test_resolves_writes_and_prunes(self, tmp_path: Path):
        sha = "c" * 40
        # setup-python@v5 already pinned; a stale entry should be pruned.
        _write_lockfile(
            tmp_path,
            **{
                "actions/setup-python@v5": "d" * 40,
                "actions/stale@v1": "e" * 40,
            },
        )
        app = _app_with_refs(
            tmp_path,
            "actions/checkout@v4",
            "actions/setup-python@v5",
        )
        client = GitHubClient(FakeTransport({"git/ref/tags/v4": _commit(sha)}))

        report = pin(app, client, update=False, prune=True)

        # Only the unpinned checkout ref was resolved.
        assert [r.uses for r in report.resolved] == ["actions/checkout@v4"]
        assert report.resolved[0].sha == sha
        assert report.pruned == 1
        assert report.written is True
        assert not report.up_to_date

        # The on-disk lockfile reflects the new pin and the prune.
        lockfile = read_lockfile(tmp_path / ".ghagen.lock.yml")
        assert lockfile.get("actions/checkout@v4").sha == sha  # type: ignore[union-attr]
        assert "actions/stale@v1" not in lockfile

    def test_up_to_date(self, tmp_path: Path):
        _write_lockfile(tmp_path, **{"actions/checkout@v4": "a" * 40})
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        client = GitHubClient(FakeTransport({}))

        report = pin(app, client, update=False, prune=True)

        assert report.resolved == []
        assert report.pruned == 0
        assert report.written is False
        assert report.up_to_date is True


# -- upgrade ---------------------------------------------------------------


class TestUpgrade:
    def test_detects_version_bump(self, tmp_path: Path):
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        source = tmp_path / "wf.py"
        source.write_text('Step(uses="actions/checkout@v4")\n')
        client = GitHubClient(FakeTransport({"git/refs/tags": _tags("v4", "v5")}))

        report = upgrade(app, client, {source}, mode="versions", apply=False)

        assert len(report.version_bumps) == 1
        bump = report.version_bumps[0]
        assert bump.uses == "actions/checkout@v4"
        assert bump.latest == "v5"
        assert bump.severity == "major"
        assert str(source) in bump.source_files
        # Dry run: nothing applied, source untouched.
        assert report.changed_files == []
        assert "actions/checkout@v4" in source.read_text()

    def test_applies_version_bump(self, tmp_path: Path):
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        source = tmp_path / "wf.py"
        source.write_text('Step(uses="actions/checkout@v4")\n')
        client = GitHubClient(FakeTransport({"git/refs/tags": _tags("v4", "v5")}))

        report = upgrade(app, client, {source}, mode="versions", apply=True)

        assert report.changed_files == [source]
        assert "actions/checkout@v5" in source.read_text()

    def test_detects_bump_to_divergent_shape_tag(self, tmp_path: Path):
        """A four-segment tag is a version tag, end to end, in both ports.

        The shared grammar (``schema/tag-grammar.yml``) accepts arity > 3, so
        ``v4.1.2.3`` is a real upgrade candidate. This is the source-file
        mutation guard: before 14, TypeScript's SemVer rejected the tag and
        left the file untouched while Python rewrote it.
        """
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        source = tmp_path / "wf.py"
        source.write_text('Step(uses="actions/checkout@v4")\n')
        client = GitHubClient(FakeTransport({"git/refs/tags": _tags("v4", "v4.1.2.3")}))

        report = upgrade(app, client, {source}, mode="versions", apply=False)

        assert len(report.version_bumps) == 1
        bump = report.version_bumps[0]
        assert bump.latest == "v4.1.2.3"
        assert bump.severity == "minor"

    def test_detects_stale_lockfile_entry(self, tmp_path: Path):
        old_sha = "a" * 40
        new_sha = "f" * 40
        _write_lockfile(tmp_path, **{"actions/checkout@v4": old_sha})
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        client = GitHubClient(FakeTransport({"git/ref/tags/v4": _commit(new_sha)}))

        report = upgrade(app, client, set(), mode="lockfile", apply=False)

        assert len(report.lockfile_stale) == 1
        stale = report.lockfile_stale[0]
        assert stale.uses == "actions/checkout@v4"
        assert stale.current_sha == old_sha
        assert stale.latest_sha == new_sha

    def test_non_version_tag_ref_is_never_a_bump(self, tmp_path: Path):
        """``@main`` is not a version tag, so it is not an upgrade candidate.

        Moved here from ``test_cli/test_deps.py::TestUpgradeNonSemver``, which
        asserted it through a CliRunner and a JSON payload.  The grammar itself
        is pinned by ``schema/tag-grammar.yml`` (``main`` -> null); this is the
        engine's half — a ref the grammar rejects yields no bump even when the
        repo has plenty of newer version tags.
        """
        app = _app_with_refs(tmp_path, "actions/checkout@main")
        source = tmp_path / "wf.py"
        source.write_text('Step(uses="actions/checkout@main")\n')
        client = GitHubClient(
            FakeTransport({"git/refs/tags": _tags("v1", "v2", "v3", "v4", "v5")})
        )

        report = upgrade(app, client, {source}, mode="versions", apply=True)

        assert report.version_bumps == []
        assert report.changed_files == []
        assert "actions/checkout@main" in source.read_text()

    def test_no_refs_returns_empty(self, tmp_path: Path):
        app = _app_without_refs(tmp_path)
        client = GitHubClient(FakeTransport({}))

        report = upgrade(app, client, set(), mode="all", apply=True)

        assert report.version_bumps == []
        assert report.lockfile_stale == []
        assert report.changed_files == []

    def test_api_error_continues_with_warning(self, tmp_path: Path):
        """A failed ``list_tags`` is recorded as a warning, not raised.

        Moved here from ``test_cli/test_deps.py``: it asserts an engine fact
        (``report.warnings``), and a canned transport scripted to answer the
        tag list with a 500 covers it without a CLI runner.
        """
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        client = GitHubClient(
            FakeTransport(
                {
                    "git/refs/tags": canned(
                        {"message": "boom"}, status=500, reason="Internal Server Error"
                    )
                }
            )
        )

        report = upgrade(app, client, set(), mode="versions", apply=False)

        assert report.version_bumps == []
        assert len(report.warnings) == 1
        assert "failed to list tags for actions/checkout" in report.warnings[0]

    def test_groups_repos_by_code_point(self, tmp_path: Path):
        """Repos are grouped for the ``list_tags`` sweep by code point.

        Companion to the TypeScript peer's regression for
        ``docs/issues/23`` item 1: ``sorted()`` on the ``(owner, repo)``
        tuples already sorts by code point here (this is the reference
        side, not the fix site), but this pins that fact against drift and
        proves both ports agree with the shared oracle
        ``fixtures/expected/pin_repo_group_order.txt`` -- the order a
        locale-aware comparator (the pre-fix TypeScript ``localeCompare``)
        would get backwards, since ``Z`` (0x5A) sorts before ``a`` (0x61) by
        code point but dictionary collation puts lowercase-initial words
        first.
        """
        app = _app_with_refs(tmp_path, "Zulu/repo@v4", "apple/repo@v4")
        client = GitHubClient(
            FakeTransport(
                {
                    "repos/Zulu/repo/git/refs/tags": _tags("v4", "v5"),
                    "repos/apple/repo/git/refs/tags": _tags("v4", "v9"),
                }
            )
        )

        report = upgrade(app, client, set(), mode="versions", apply=False)

        expected = (EXPECTED_DIR / "pin_repo_group_order.txt").read_text().splitlines()
        assert [b.uses for b in report.version_bumps] == expected


# -- upgrade: what the run was asked to check ------------------------------


class TestUpgradeCheckedFlags:
    """``checked_versions`` / ``checked_lockfile`` are pure functions of *mode*.

    They record what the run was *asked for*, so the renderer never has to
    re-derive it from the CLI's ``--mode``.  "Asked for" is not "ran": with no
    lockfile configured the lockfile stage is skipped and the flag stays True.
    """

    @pytest.mark.parametrize(
        ("mode", "versions", "lockfile"),
        [
            ("versions", True, False),
            ("lockfile", False, True),
            ("all", True, True),
        ],
    )
    def test_flags_follow_mode(
        self, tmp_path: Path, mode: str, versions: bool, lockfile: bool
    ):
        app = _app_with_refs(tmp_path, "actions/checkout@v4")
        client = GitHubClient(FakeTransport({"git/refs/tags": _tags("v4")}))

        report = upgrade(app, client, set(), mode=mode, apply=False)  # type: ignore[arg-type]

        assert report.checked_versions is versions
        assert report.checked_lockfile is lockfile

    @pytest.mark.parametrize(
        ("mode", "versions", "lockfile"),
        [
            ("versions", True, False),
            ("lockfile", False, True),
            ("all", True, True),
        ],
    )
    def test_no_refs_report_still_reports_checked_flags(
        self, tmp_path: Path, mode: str, versions: bool, lockfile: bool
    ):
        """The flags are set *before* the no-refs early return.

        This ordering is the fact the whole renderer design turns on: a
        project with no pinnable refs must render the same JSON key set as
        any other, so the flags cannot be set after the early return.
        """
        app = _app_without_refs(tmp_path)
        client = GitHubClient(FakeTransport({}))

        report = upgrade(app, client, set(), mode=mode, apply=True)  # type: ignore[arg-type]

        assert report.version_bumps == []
        assert report.lockfile_stale == []
        assert report.checked_versions is versions
        assert report.checked_lockfile is lockfile

    def test_checked_lockfile_is_true_without_a_lockfile(self, tmp_path: Path):
        """ "Asked for" is not "ran" — ``lockfile=None`` skips the stage."""
        app = App(root=tmp_path, lockfile=None)
        wf = Workflow(
            name="CI",
            on=On(push=PushTrigger(branches=["main"])),
            jobs={
                "test": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        app.add_workflow(wf, "ci.yml")
        client = GitHubClient(FakeTransport({}))

        report = upgrade(app, client, set(), mode="lockfile", apply=False)

        assert report.checked_lockfile is True
        assert report.lockfile_stale == []
