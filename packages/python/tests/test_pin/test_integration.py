"""Integration tests: full pin → synth pipeline and CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from ghagen.app import App
from ghagen.models.job import Job
from ghagen.models.step import Step
from ghagen.models.trigger import On, PushTrigger
from ghagen.models.workflow import Workflow
from ghagen.pin.lockfile import Lockfile, PinEntry, write_lockfile
from ghagen.pin.transform import PinError

SHA_CHECKOUT = "a" * 40
SHA_SETUP_PY = "b" * 40
SAMPLE_TIME = datetime(2026, 4, 9, tzinfo=UTC)


def _write_lockfile(root: Path, **pins: str) -> Path:
    """Write a lockfile to ``root/.github/ghagen.lock.toml``."""
    lf = Lockfile(
        pins={
            uses: PinEntry(sha=sha, resolved_at=SAMPLE_TIME)
            for uses, sha in pins.items()
        }
    )
    lockfile_path = root / ".github" / "ghagen.lock.toml"
    write_lockfile(lf, lockfile_path)
    return lockfile_path


class TestSynthWithPin:
    """End-to-end: create App + lockfile, synth, verify YAML output."""

    def test_pinned_yaml_has_sha_and_comment(self, tmp_path):
        _write_lockfile(
            tmp_path,
            **{
                "actions/checkout@v4": SHA_CHECKOUT,
                "actions/setup-python@v5": SHA_SETUP_PY,
            },
        )
        app = App(root=tmp_path)
        wf = Workflow(
            name="CI",
            on=On(push=PushTrigger(branches=["main"])),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[
                        Step(uses="actions/checkout@v4"),
                        Step(
                            uses="actions/setup-python@v5",
                            with_={"python-version": "3.12"},
                        ),
                        Step(name="Test", run="pytest"),
                    ],
                ),
            },
        )
        app.add_workflow(wf, "ci.yml")
        written = app.synth()

        assert len(written) == 1
        content = written[0].read_text()

        # SHAs should be in the output.
        assert SHA_CHECKOUT in content
        assert SHA_SETUP_PY in content

        # Original refs should be in end-of-line comments.
        assert "# v4" in content
        assert "# v5" in content

        # The run step should be unaffected.
        assert "pytest" in content

    def test_no_lockfile_passes_through(self, tmp_path):
        """Without a lockfile, synth emits the original refs."""
        app = App(root=tmp_path)
        wf = Workflow(
            name="CI",
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                ),
            },
        )
        app.add_workflow(wf, "ci.yml")
        written = app.synth()
        content = written[0].read_text()
        assert "actions/checkout@v4" in content
        assert SHA_CHECKOUT not in content

    def test_lockfile_disabled(self, tmp_path):
        """When lockfile=None, the lockfile is never loaded."""
        _write_lockfile(tmp_path, **{"actions/checkout@v4": SHA_CHECKOUT})
        app = App(root=tmp_path, lockfile=None)
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        app.add_workflow(wf, "ci.yml")
        written = app.synth()
        content = written[0].read_text()
        assert "actions/checkout@v4" in content
        assert SHA_CHECKOUT not in content

    def test_missing_lockfile_entry_errors(self, tmp_path):
        """If the lockfile exists but is missing an entry, synth errors."""
        _write_lockfile(tmp_path)  # empty lockfile
        app = App(root=tmp_path)
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        app.add_workflow(wf, "ci.yml")
        with pytest.raises(PinError, match="No lockfile entry"):
            app.synth()

    def test_synth_idempotent(self, tmp_path):
        """Synth doesn't mutate original models — can be called twice."""
        _write_lockfile(tmp_path, **{"actions/checkout@v4": SHA_CHECKOUT})
        app = App(root=tmp_path)
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        app.add_workflow(wf, "ci.yml")
        app.synth()
        # Original model should be unchanged.
        assert wf.jobs["build"].steps[0].uses == "actions/checkout@v4"
        # Second synth should produce identical output.
        app.synth()
        content = (tmp_path / ".github" / "workflows" / "ci.yml").read_text()
        assert SHA_CHECKOUT in content


class TestCheckWithPin:
    def test_check_passes_with_pinned(self, tmp_path):
        _write_lockfile(tmp_path, **{"actions/checkout@v4": SHA_CHECKOUT})
        app = App(root=tmp_path)
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        app.add_workflow(wf, "ci.yml")
        app.synth()
        stale = app.check()
        assert stale == []

    def test_check_detects_stale(self, tmp_path):
        _write_lockfile(tmp_path, **{"actions/checkout@v4": SHA_CHECKOUT})
        app = App(root=tmp_path)
        wf = Workflow(
            on=On(push=PushTrigger()),
            jobs={
                "build": Job(
                    runs_on="ubuntu-latest",
                    steps=[Step(uses="actions/checkout@v4")],
                )
            },
        )
        app.add_workflow(wf, "ci.yml")
        # Write a file that doesn't match.
        out = tmp_path / ".github" / "workflows" / "ci.yml"
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text("stale content")
        stale = app.check()
        assert len(stale) == 1
