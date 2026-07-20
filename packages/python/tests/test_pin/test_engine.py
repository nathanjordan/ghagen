"""Unit tests for the pin engine (pin / check_sync / upgrade).

``check_sync`` needs no client at all; ``pin`` and ``upgrade`` are driven
through a :class:`GitHubClient` backed by a canned ``FakeTransport`` (no
network) plus tmp dirs.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path

from ghagen.app import App
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.engine import check_sync, pin, upgrade
from ghagen.pin.github import GitHubClient, Response
from ghagen.pin.lockfile import Lockfile, PinEntry, read_lockfile, write_lockfile

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


def _write_lockfile(root: Path, **pins: str) -> Path:
    lf = Lockfile(
        pins={u: PinEntry(sha=sha, resolved_at=SAMPLE_TIME) for u, sha in pins.items()}
    )
    path = root / ".ghagen.lock.yml"
    write_lockfile(lf, path)
    return path


class FakeTransport:
    """Canned HttpClient keyed by URL substring (mirrors test_github)."""

    def __init__(self, responses: dict[str, object]) -> None:
        self._responses = responses
        self.calls: list[str] = []

    def get(self, url: str, *, token: str | None = None) -> Response:
        self.calls.append(url)
        for pattern, value in self._responses.items():
            if pattern in url:
                assert isinstance(value, Response)
                return value
        return Response(status=404, body=b"{}", reason="Not Found")


def _json_response(obj: object) -> Response:
    return Response(status=200, body=json.dumps(obj).encode(), reason="")


def _commit(sha: str) -> Response:
    return _json_response({"object": {"type": "commit", "sha": sha}})


def _tags(*names: str) -> Response:
    return _json_response([{"ref": f"refs/tags/{n}"} for n in names])


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

    def test_no_refs_returns_empty(self, tmp_path: Path):
        app = App(root=tmp_path)
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
        client = GitHubClient(FakeTransport({}))

        report = upgrade(app, client, set(), mode="all", apply=True)

        assert report.version_bumps == []
        assert report.lockfile_stale == []
        assert report.changed_files == []
